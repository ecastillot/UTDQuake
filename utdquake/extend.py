"""
Extend UTDQuake networks with more events from their providers, reproducibly.

A *recipe* (CSV, kept in the repository: ``datasets/extend/<version>.csv``) says, for each UTDQuake network,
where its events come from (FDSN provider, contributor, extra query parameters), how many it should reach
(``target``, after QC) and in which time window. The steps read it and log what they did in
``<root>/.utdquake/extend/<version>/<utdq_net>.json`` (queries, windows, counts, code commit), so an
extension can be rerun and audited.

New events go to a bank of their own, ``<root>/.utdquake/extend/<version>/banks/<utdq_net>``: the network's
bank and tables are not touched until the new events are processed and checked. Picks come with the events
(``includearrivals``) or, for ComCat (USGS), from each event's ``phase-data`` product
(:func:`utdquake.bank.fdsn.comcat_phase_data`).

    python -m utdquake.extend recipe <version> [--target 20000] [--end 2026-11-01]
    python -m utdquake.extend download <version> <utdq_net> [--workers 8]
    python -m utdquake.extend run <version> --provider ISC [--parallel 4] [--hours 46]
    python -m utdquake.extend status <version>
    python -m utdquake.extend stations <version> <utdq_net>   # coordinates of stations UTDQuake lacks
    python -m utdquake.extend stage <version> <utdq_net>      # stations, pick QC, tables of the new events

Download order: first forward, from the network's newest event to the recipe's ``endtime``, then backward,
from its oldest event to ``starttime``, until the bank holds ``ceil(target * margin)`` events (existing plus
new; ``margin`` leaves room for the events QC removes). Rerunning resumes: the windows start where the new
bank ends.
"""
from __future__ import annotations

import argparse
import datetime
import json
import logging
import math
import os
import re
import sqlite3
import subprocess
from contextlib import contextmanager
from pathlib import Path

import obsplus
import pandas as pd
from obspy import UTCDateTime

from utdquake.core.config import get_hf_entry, get_root

logger = logging.getLogger(__name__)

#: Providers of the v1 networks (obspy FDSN client keys) and the contributor of each network.
PROVIDERS = {"ISC": "ISC", "USGS": "USGS", "ETH": "ETH", "GEOFON": "GEOFON"}
#: Networks whose v1 events came from the agency's own FDSN service, although the networks table lists
#: ISC (their event ids are SeisComP ids of the agency): utdq_net -> provider of :data:`CLIENTS`.
OWN_SERVICE = {"NOA": "NOA", "IPGP": "IPGP"}
#: FDSN client of each recipe provider that is not an ObsPy key (NOA's service needs https).
CLIENTS = {"NOA": "https://eida.gein.noa.gr"}
#: Networks whose events have no contributor of their own in the provider's service.
NO_CONTRIBUTOR = {"ETH", "GEOFON", "NOA", "IPGP"}
#: Extra event-query parameters of networks that are a selection of a provider's catalog.
QUERIES = {"R08": {"mindepth": 30}}
#: Where to look for events (v1 searched back to 2010).
START = "2010-01-01"
#: Bank layout of every UTDQuake network (as in v1).
PATH_STRUCTURE, NAME_STRUCTURE = "{year}/{month}/{day}", "{event_id_end}"
MARGIN = 1.05
#: Days per request (a fuller window is split by Client.events_in, so none is cut short). v1 used one day;
#: a week costs ISC 7x fewer requests and the bank 7x fewer writes, which took most of the time.
CHUNK_DAYS = 7
#: Providers asked in shorter windows: NOA refuses a day of events with picks as too large (413).
PROVIDER_CHUNK_DAYS = {"NOA": 0.25}
RECIPE_COLUMNS = ["utdq_net", "provider", "contributor", "query", "target", "margin", "starttime", "endtime"]


def _commit() -> str:
    here = Path(__file__).resolve().parent
    out = subprocess.run(["git", "-C", str(here), "rev-parse", "--short", "HEAD"], capture_output=True, text=True)
    dirty = subprocess.run(["git", "-C", str(here), "status", "--porcelain", "--", str(here)],
                           capture_output=True, text=True).stdout.strip()
    return (out.stdout.strip() or "unknown") + ("+changes" if dirty else "")


def work_dir(version: str) -> Path:
    return get_root() / ".utdquake" / "extend" / version


def recipe_path(version: str) -> Path:
    return Path(__file__).resolve().parents[1] / "datasets" / "extend" / f"{version}.csv"


def networks_table() -> pd.DataFrame:
    return pd.read_parquet(get_root() / get_hf_entry("networks").path)


def make_recipe(version: str, target: int = 20000, endtime: str | None = None, extra: list[dict] | None = None,
                ) -> pd.DataFrame:
    """The recipe of an extension: every network of a provider in :data:`PROVIDERS` (and the selections in
    :data:`QUERIES`), plus ``extra`` rows (new networks). Written to :func:`recipe_path`."""
    endtime = endtime or datetime.date.today().isoformat()
    table = networks_table()
    rows = []
    for _, net in table.sort_values("utdq_net").iterrows():
        code = net["utdq_net"]
        provider = OWN_SERVICE.get(code) or PROVIDERS.get(str(net["provider"]))
        if provider is None:
            continue
        query = QUERIES.get(code, {})
        contributor = None if (code in NO_CONTRIBUTOR or query) else code
        rows.append({"utdq_net": code, "provider": provider, "contributor": contributor,
                     "query": json.dumps(query), "target": target, "margin": MARGIN,
                     "starttime": START, "endtime": endtime})
    for row in extra or []:
        rows.append({**{"query": "{}", "target": target, "margin": MARGIN, "starttime": START,
                        "endtime": endtime}, **row})
    recipe = pd.DataFrame(rows, columns=RECIPE_COLUMNS)
    path = recipe_path(version)
    path.parent.mkdir(parents=True, exist_ok=True)
    recipe.to_csv(path, index=False)
    logger.info("Recipe of %s: %d networks -> %s", version, len(recipe), path)
    return recipe


def read_recipe(version: str) -> pd.DataFrame:
    return pd.read_csv(recipe_path(version), dtype={"contributor": object}, keep_default_na=False,
                       na_values={"contributor": [""]})


def _bank(path: Path) -> obsplus.EventBank:
    path.mkdir(parents=True, exist_ok=True)
    return obsplus.EventBank(base_path=path, path_structure=PATH_STRUCTURE, name_structure=NAME_STRUCTURE,
                             format="quakeml")


def _times(bank: obsplus.EventBank) -> pd.Series:
    index = bank.read_index()
    return pd.to_datetime(index["time"]) if len(index) else pd.Series(dtype="datetime64[ns]")


def existing(utdq_net: str) -> dict:
    """Events of the network in the working copy: count, first and last origin time."""
    events = pd.read_parquet(get_root() / get_hf_entry("events").path.format(utdq_net=utdq_net), columns=["time"])
    t = pd.to_datetime(events["time"])
    return {"events": len(t), "first": t.min(), "last": t.max()}


def _log(version: str, utdq_net: str, entry: dict) -> None:
    path = work_dir(version) / f"{utdq_net}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    log = json.loads(path.read_text()) if path.exists() else []
    log.append(entry)
    path.write_text(json.dumps(log, indent=1, default=str))


def download(version: str, utdq_net: str, workers: int = 8) -> dict:
    """Download the new events of one network (see the module docstring for the order and the windows)."""
    from utdquake.bank.fdsn import NoEvents, new_client

    row = read_recipe(version).set_index("utdq_net").loc[utdq_net]
    query = json.loads(row["query"] or "{}")
    contributor = row["contributor"] if isinstance(row["contributor"], str) else None
    old = existing(utdq_net) if (get_root() / "events" / f"utdq_net={utdq_net}.parquet").exists() else \
        {"events": 0, "first": pd.Timestamp(row["endtime"]), "last": pd.Timestamp(row["endtime"])}
    cap = math.ceil(row["target"] * row["margin"])
    bank_path = work_dir(version) / "banks" / utdq_net
    bank = _bank(bank_path)
    bank.update_index()  # events written by a run stopped before indexing them count too
    before = len(_times(bank))
    client = new_client(CLIENTS.get(row["provider"], row["provider"]))
    chunk_days = PROVIDER_CHUNK_DAYS.get(row["provider"], CHUNK_DAYS)
    start, end = UTCDateTime(row["starttime"]), UTCDateTime(row["endtime"])
    entry = {"step": "download", "date": datetime.datetime.now().isoformat(timespec="seconds"),
             "commit": _commit(), "provider": client.base_url, "contributor": contributor, "query": query,
             "existing": old, "cap": cap, "chunk_days": chunk_days, "windows": []}

    for direction in ("forward", "backward"):
        new = _times(bank)
        remaining = cap - old["events"] - len(new)
        if remaining <= 0:
            break
        if direction == "forward":
            done = new[new > old["last"]]
            t0 = UTCDateTime((done.max() if len(done) else old["last"]).to_pydatetime()) + 1
            t1 = end
        else:
            done = new[new < old["first"]]
            t0 = start
            t1 = UTCDateTime((done.min() if len(done) else old["first"]).to_pydatetime()) - 1
        if t1 <= t0:
            continue
        chunks = math.ceil((t1 - t0) / (chunk_days * 86400)) + 1
        before = len(new)
        try:
            client.download_events(events_bank_path=str(bank_path), starttime=t0, endtime=t1,
                                   path_structure=PATH_STRUCTURE, name_structure=NAME_STRUCTURE,
                                   max_n_events=remaining, max_from_bank=False, chunk_seconds=chunk_days * 86400,
                                   patience=chunks, reverse=(direction == "backward"), workers=workers,
                                   contributor=contributor, **query)
            msg = None
        except NoEvents:
            msg = None  # the window is empty: done
        except Exception as e:
            msg = f"{type(e).__name__}: {e}"
            logger.warning("%s %s %s-%s: %s", utdq_net, direction, t0, t1, msg)
        entry["windows"].append({"direction": direction, "start": str(t0), "end": str(t1),
                                 "new_events": len(_times(bank)) - before, "error": msg})

    entry["new_events"] = len(_times(bank))
    entry["added"] = entry["new_events"] - before
    entry["total"] = old["events"] + entry["new_events"]
    # complete: at the cap, or every window ran to its end (the provider has no more events)
    entry["complete"] = entry["total"] >= cap or all(w["error"] is None for w in entry["windows"])
    _log(version, utdq_net, entry)
    logger.info("%s: %d existing + %d new = %d (cap %d)", utdq_net, old["events"], entry["new_events"],
                entry["total"], cap)
    return entry


def _last(version: str, utdq_net: str, step: str = "download") -> dict:
    """The last entry of one step in a network's log."""
    path = work_dir(version) / f"{utdq_net}.json"
    entries = [e for e in json.loads(path.read_text()) if e.get("step") == step] if path.exists() else []
    return entries[-1] if entries else {}


def _provider_url(provider: str) -> str:
    from obspy.clients.fdsn.header import URL_MAPPINGS
    key = CLIENTS.get(provider, provider)
    return URL_MAPPINGS.get(key.upper(), key)


def _complete(version: str, utdq_net: str, provider: str) -> bool:
    """The last download of the network is complete and asked the recipe's provider (a network moved to
    another provider, as NOA and IPGP, is downloaded again)."""
    from urllib.parse import urlparse
    last = _last(version, utdq_net)
    host = lambda url: urlparse(str(url)).netloc
    return bool(last.get("complete")) and host(last.get("provider")) == host(_provider_url(provider))


def _download_logged(args):
    version, utdq_net, workers = args
    try:
        return download(version, utdq_net, workers)
    except Exception as e:
        logger.exception("%s: download failed", utdq_net)
        _log(version, utdq_net, {"step": "download", "date": datetime.datetime.now().isoformat(timespec="seconds"),
                                  "commit": _commit(), "complete": False, "error": f"{type(e).__name__}: {e}"})
        return {"utdq_net": utdq_net, "error": str(e)}


def run(version: str, provider: str, parallel: int = 1, workers: int = 2, hours: float = 46) -> list:
    """Download every incomplete network of ``provider`` (comma-separated providers) in the recipe: at most
    ``parallel`` networks of each provider at a time (one: the providers limit the request rate), the providers
    at the same time. No network is started after ``hours`` (a job's time limit; rerun to continue). Returns
    the networks worth another run: not started (time limit) or incomplete after gaining events. A network
    that ended incomplete without new events (a window failing again, or a provider without picks there)
    is not: the next job would only repeat it."""
    import concurrent.futures as cf
    import time

    deadline = time.time() + hours * 3600
    providers = provider.split(",")
    recipe = read_recipe(version).query("provider in @providers")
    of = dict(zip(recipe["utdq_net"], recipe["provider"]))
    todo = [n for n in recipe["utdq_net"] if not _complete(version, n, of[n])]
    logger.info("%s, %s: %d networks to download", version, provider, len(todo))
    pending = list(todo)
    gained = {}
    with cf.ProcessPoolExecutor(max_workers=parallel * len(providers)) as pool:
        running = {}
        while pending or running:
            busy = [of[n] for n in running.values()]
            for net in list(pending):
                if time.time() < deadline and busy.count(of[net]) < parallel:
                    pending.remove(net)
                    busy.append(of[net])
                    running[pool.submit(_download_logged, (version, net, workers))] = net
            if not running:
                break
            done, _ = cf.wait(running, return_when=cf.FIRST_COMPLETED)
            for f in done:
                net, result = running.pop(f), f.result()
                gained[net] = result.get("added", 0) > 0
                logger.info("%s finished: %s", net, {k: v for k, v in result.items()
                                                     if k in ("total", "added", "complete", "error")})
    left = [n for n in todo if not _complete(version, n, of[n])]
    stuck = [n for n in left if n in gained and not gained[n]]
    if stuck:
        logger.warning("incomplete without new events (not rerun; see their windows): %s", stuck)
    return [n for n in left if n not in stuck]


def status(version: str) -> pd.DataFrame:
    """Per network: existing events, new events downloaded so far, and the target."""
    rows = []
    for _, row in read_recipe(version).iterrows():
        net = row["utdq_net"]
        path = work_dir(version) / "banks" / net / ".index.db"
        new = len(obsplus.EventBank(path.parent).read_index()) if path.exists() else 0
        events = get_root() / get_hf_entry("events").path.format(utdq_net=net)
        old = len(pd.read_parquet(events, columns=["event_id"])) if events.exists() else 0
        rows.append({"utdq_net": net, "provider": row["provider"], "existing": old, "new": new, "total": old + new,
                     "target": row["target"], "complete": _complete(version, net, row["provider"])})
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------------------------------------------
# Processing: the new events of a network get station coordinates, pick QC and tables of their own, in a
# staging root (``<work>/stage``, laid out like a UTDQuake root), as v1 did. They reach the network's tables
# only at the merge, which appends rows: rows of earlier versions are never rebuilt.

#: Station services asked for stations UTDQuake has no coordinates of, after the provider's own (if it has
#: one): the IRIS federator routes to every FDSN data centre. ISC has none: its ``IR`` stations are located
#: from its registry (the IR step).
STATION_SERVICES = {"ETH": "ETH", "GEOFON": "GEOFON", "NOA": "https://eida.gein.noa.gr", "IPGP": "IPGP"}
FEDERATOR = "iris-federator"
STATION_COLUMNS = ["network", "station", "latitude", "longitude", "elevation", "source", "service", "date",
                   "utdq_net"]
#: Days of new events attached to their stations at a time.
STAGE_DAYS = 30
_WAVEFORM_ID = re.compile(rb"<waveformID\b([^>]*)>")
_NETWORK_CODE = re.compile(rb'networkCode="([^"]*)"')
_STATION_CODE = re.compile(rb'stationCode="([^"]*)"')


def stage_root(version: str) -> Path:
    return work_dir(version) / "stage"


@contextmanager
def _root(path: Path):
    """UTDQuake functions read and write under ``path`` (UTDQUAKE_ROOT) inside the block."""
    before = os.environ.get("UTDQUAKE_ROOT")
    os.environ["UTDQUAKE_ROOT"] = str(path)
    try:
        yield path
    finally:
        if before is None:
            os.environ.pop("UTDQUAKE_ROOT", None)
        else:
            os.environ["UTDQUAKE_ROOT"] = before


def known_stations() -> pd.DataFrame:
    """Confirmed station coordinates of the working copy, by the codes the providers report (the station
    database of each row: ``.<network>_<station>.db``), all networks. ``IR`` stations are left out: they are
    located by the IR step, as in v1."""
    rows = []
    for path in sorted((get_root() / "stations").glob("utdq_net=*.parquet")):
        df = pd.read_parquet(path, columns=["db_path", "confirmed", "confirmed_latitude", "confirmed_longitude",
                                            "confirmed_elevation", "network_type"])
        rows.append(df[df["confirmed"].fillna(False).astype(bool)])
    df = pd.concat(rows, ignore_index=True)
    codes = df["db_path"].str.extract(r"/\.([^_/]+)_([^/]+)\.db$")
    df = pd.DataFrame({"network": codes[0], "station": codes[1], "latitude": df["confirmed_latitude"],
                       "longitude": df["confirmed_longitude"], "elevation": df["confirmed_elevation"],
                       "network_type": df["network_type"].fillna("surface"), "source": "utdquake"})
    df = df.dropna(subset=["network", "station", "latitude", "longitude"])
    return df[df["network"] != "IR"].drop_duplicates(["network", "station"], ignore_index=True)


def pick_codes(bank_path: Path) -> set:
    """(network, station) of every pick in the QuakeML files of a bank (read as text: fast)."""
    codes = set()
    for path in Path(bank_path).rglob("*.xml"):
        for attrs in _WAVEFORM_ID.findall(path.read_bytes()):
            net, sta = _NETWORK_CODE.search(attrs), _STATION_CODE.search(attrs)
            if sta:
                codes.add(((net.group(1) if net else b"").decode(), sta.group(1).decode()))
    return codes


def _ask_stations(service: str, codes: list) -> pd.DataFrame:
    """Coordinates of ``codes`` from one FDSN station service (per network, 50 stations a request, paced
    and retried); the newest epoch of each station."""
    from obspy.clients.fdsn import RoutingClient
    from obspy.clients.fdsn.header import FDSNException, FDSNNoDataException

    from utdquake.bank.fdsn import _patiently, _throttle, new_client
    client = RoutingClient(service) if service == FEDERATOR else new_client(service)
    url = "http://service.iris.edu" if service == FEDERATOR else client.base_url
    rows = []
    by_net = pd.DataFrame(codes, columns=["network", "station"]).groupby("network")["station"]
    for net, stations in by_net:
        stations = sorted(stations)
        for i in range(0, len(stations), 50):
            part = stations[i:i + 50]

            def once():
                _throttle(url)
                try:
                    return client.get_stations(network=net, station=",".join(part), level="station")
                except FDSNException as e:
                    if "404" in str(e):  # the federator's answer for "no such station"
                        raise FDSNNoDataException(str(e)) from e
                    raise
            try:
                inventory = _patiently(once, f"get_stations {service} {net}")
            except FDSNNoDataException:
                continue
            for network in inventory:
                for station in network:
                    rows.append({"network": network.code, "station": station.code, "latitude": station.latitude,
                                 "longitude": station.longitude, "elevation": station.elevation,
                                 "start": station.start_date})
    df = pd.DataFrame(rows, columns=["network", "station", "latitude", "longitude", "elevation", "start"])
    df = df.sort_values("start").drop_duplicates(["network", "station"], keep="last").drop(columns="start")
    return df[df.set_index(["network", "station"]).index.isin(codes)]


def stations(version: str, utdq_net: str) -> pd.DataFrame:
    """Coordinates of the stations picked in the new events of a network that UTDQuake has none of: asked of
    the provider's station service, then the IRIS federator. Appended to ``<work>/stations.csv`` with the
    service and date (stations not found too, without coordinates, so they are not asked again)."""
    row = read_recipe(version).set_index("utdq_net").loc[utdq_net]
    path = work_dir(version) / "stations.csv"
    cache = pd.read_csv(path, keep_default_na=False, na_values={c: [""] for c in ("latitude", "longitude",
                                                                                  "elevation")}) \
        if path.exists() else pd.DataFrame(columns=STATION_COLUMNS)
    have = set(map(tuple, known_stations()[["network", "station"]].values)) | \
        set(map(tuple, cache[["network", "station"]].astype(str).values))
    picked = pick_codes(work_dir(version) / "banks" / utdq_net)
    missing = sorted(c for c in picked - have if c[0] not in ("IR", ""))
    logger.info("%s: %d stations picked, %d without coordinates", utdq_net, len(picked), len(missing))
    found = []
    for service in [STATION_SERVICES.get(row["provider"]), FEDERATOR]:
        if service is None or not missing:
            continue
        df = _ask_stations(service, missing)
        df["service"] = service
        found.append(df)
        missing = sorted(set(missing) - set(map(tuple, df[["network", "station"]].values)))
        logger.info("%s: %d stations from %s, %d still missing", utdq_net, len(df), service, len(missing))
    found.append(pd.DataFrame({"network": [c[0] for c in missing], "station": [c[1] for c in missing],
                               "service": None}))
    # (with no station missing, no service was asked: the frame has no coordinate columns)
    new = pd.concat(found, ignore_index=True).reindex(columns=STATION_COLUMNS)
    new["source"] = new["latitude"].notna().map({True: "fdsn", False: "not_found"})
    new["date"] = datetime.date.today().isoformat()
    new["utdq_net"] = utdq_net
    pd.concat([cache, new[STATION_COLUMNS]], ignore_index=True).to_csv(path, index=False)
    entry = {"step": "stations", "date": datetime.datetime.now().isoformat(timespec="seconds"),
             "commit": _commit(), "picked": len(picked),
             "asked": int(len(new)), "found": int(new["latitude"].notna().sum()),
             "services": new.dropna(subset=["latitude"])["service"].value_counts().to_dict(),
             "not_found": int(new["latitude"].isna().sum())}
    _log(version, utdq_net, entry)
    return new


def station_table(version: str) -> pd.DataFrame:
    """Every station coordinate for the processing: UTDQuake's, then those asked by :func:`stations`."""
    path = work_dir(version) / "stations.csv"
    asked = pd.read_csv(path).dropna(subset=["latitude", "longitude"]) if path.exists() else pd.DataFrame()
    asked = asked.assign(network_type="surface").reindex(columns=["network", "station", "latitude", "longitude",
                                                                  "elevation", "network_type", "source"])
    df = pd.concat([known_stations(), asked], ignore_index=True)
    df["elevation"] = df["elevation"].fillna(0.0)
    return df.drop_duplicates(["network", "station"], ignore_index=True)


def version_label(version: str) -> str:
    """Label of the events a version adds (``dataset_version``), as in the network table: ``v2.0`` -> ``v2``."""
    return re.sub(r"(\.0)+$", "", version)


def stage(version: str, utdq_net: str) -> dict:
    """Process the new events of a network in the staging root, as v1 processed its events: station
    coordinates, distances and azimuths (events with more than half of their arrivals without a pick are
    dropped), the stations summary, pick QC (``put_utdq_picks``) and the events/stations/picks tables
    (``build_manifests``, ``dataset_version`` = :func:`version_label`, e.g. ``v2`` for ``v2.0``). Resumes: events already staged are skipped."""
    from utdquake.bank import utils as bank_utils
    from utdquake.bank.bank import UTDQBank
    from utdquake.writers.parquet import build_manifests

    raw = _bank(work_dir(version) / "banks" / utdq_net)
    df_stations = station_table(version)
    times = _times(raw)
    with _root(stage_root(version)) as root:
        path = root / "banks" / utdq_net
        path.mkdir(parents=True, exist_ok=True)
        bank = UTDQBank(str(path), path_structure=PATH_STRUCTURE, name_structure=NAME_STRUCTURE, format="quakeml")
        bank.update_index()
        index = bank.read_index()
        done = set(index["event_id"]) if len(index) else set()
        t, end = UTCDateTime(times.min().to_pydatetime()) - 1, UTCDateTime(times.max().to_pydatetime()) + 1
        kept = 0
        while t < end:
            t1 = min(t + STAGE_DAYS * 86400, end)
            catalog = raw.get_events(starttime=t, endtime=t1)
            catalog.events = [e for e in catalog if str(e.resource_id) not in done]
            if len(catalog):
                catalog = bank_utils.append_stations_to_catalog(catalog, df_stations,
                                                                ebank_index_path=str(path / ".index.db"))
                bank.put_events(catalog)
                done |= {str(e.resource_id) for e in catalog}
                kept += len(catalog)
            t = t1
        stations_folder = bank.utdq_paths[".utdquake/export/db/stations/.stations"]
        summary = bank_utils.get_stations_summary(stations_folder=stations_folder)
        with sqlite3.connect(bank.utdq_paths[".utdquake/export/db/stations"]) as con:
            summary.to_sql("/stations/index", con, if_exists="replace", index=False)
            pd.DataFrame({"last_updated": [datetime.datetime.now().timestamp()]}).to_sql(
                "/stations/last_updated", con, if_exists="replace", index=False)
        bank.put_utdq_picks(apply_utdq_qc=True)
        build_manifests(utdq_nets=[utdq_net], include_events=True, include_stations=True, include_picks=True,
                        include_networks=False, overwrite=True,
                        include_manual_network_info=pd.DataFrame({"utdq_net": [utdq_net],
                                                                  "dataset_version": [version_label(version)]}))
        tables = {k: root / ".utdquake" / "export" / "manifests" / k / f"utdq_net={utdq_net}.parquet"
                  for k in ("events", "stations", "picks")}
        events, picks = pd.read_parquet(tables["events"]), pd.read_parquet(tables["picks"], columns=["event_id"])
    entry = {"step": "stage", "date": datetime.datetime.now().isoformat(timespec="seconds"), "commit": _commit(),
             "downloaded": len(times), "staged": len(done), "with_stations_this_run": kept,
             "events_with_picks": int(events["event_id"].isin(picks["event_id"]).sum()), "picks": len(picks),
             "tables": {k: str(v) for k, v in tables.items()}}
    _log(version, utdq_net, entry)
    logger.info("%s staged: %s", utdq_net, entry)
    return entry


# ----------------------------------------------------------------------------------------------------------
# Merge: the staged tables of a network are appended to its tables in the working copy (rows of earlier
# versions are kept as they are), except for the networks of REPLACE, whose staged tables hold every event
# (JMA: the v1 events rebuilt with all their picks, see datasets/JMA/jma_to_utdq.py) and replace them.

#: Networks whose tables the merge replaces (their staged events include the v1 events, rebuilt).
REPLACE = {"JMA"}
#: Network-table information of the networks new in a version (the counts come from their tables).
NEW_NETWORK_INFO = {"ci": {"template": "nc", "agency": "Southern California Seismic Network"}}
_NETWORK_COUNTS = ["events", "p_arrivals", "s_arrivals", "p_count", "pg_count", "pn_count", "s_count",
                   "sg_count", "sn_count", "total_stations", "located_stations", "confirmed_stations",
                   "calculated_stations", "start_time", "end_time", "approx_lat_min", "approx_lat_max",
                   "approx_lon_min", "approx_lon_max"]


def _staged(version: str, utdq_net: str) -> dict:
    base = stage_root(version) / ".utdquake" / "export" / "manifests"
    return {k: base / k / f"utdq_net={utdq_net}.parquet" for k in ("events", "picks", "stations")}


def _like(df: pd.DataFrame, ref: pd.DataFrame) -> pd.DataFrame:
    """``df`` with the columns (order) and dtypes of ``ref`` (datetimes in the unit of ``ref``)."""
    df = df.reindex(columns=ref.columns)
    for c in ref.columns:
        dtype = ref[c].dtype
        if pd.api.types.is_datetime64_any_dtype(dtype):
            df[c] = pd.to_datetime(df[c]).astype(dtype)
        elif str(df[c].dtype) != str(dtype):
            try:
                df[c] = df[c].astype(dtype)
            except (TypeError, ValueError):
                logger.warning("column %s kept as %s (not castable to %s)", c, df[c].dtype, dtype)
    return df


def _ns(df: pd.DataFrame) -> pd.DataFrame:
    for c in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[c]):
            df[c] = df[c].astype("datetime64[ns]")
    return df


def _write(df: pd.DataFrame, path: Path, backup: Path) -> None:
    """Write a table, the file it replaces copied to ``backup`` first (once)."""
    import shutil
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not backup.exists():
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, backup)
    tmp = path.with_suffix(".tmp.parquet")
    df.to_parquet(tmp, index=False)
    os.replace(tmp, path)


def merge(version: str, utdq_net: str, root: Path | None = None) -> dict:
    """Merge the staged tables of a network into the tables of ``root`` (default: the working copy).

    Events: the staged events with picks, once each; appended to the network's events, except those already
    there (an event of an earlier version is never replaced), or, for :data:`REPLACE`, replacing them.
    Picks: those of the merged events. Stations: the staged stations not in the network's table (by network
    and station code), ``db_path`` as in v1 (``<utdq_net>/.stations/.<network>_<station>.db``). Every new row
    has ``dataset_version`` = :func:`version_label`. The network table row gets the counts of the merged
    tables (a network new in the version gets a row from :data:`NEW_NETWORK_INFO`). Each replaced file is
    copied to ``<root>/.utdquake/backups/<version>_merge/`` first. Rerunning adds nothing twice."""
    from utdquake.utils.utils import get_network_summary

    root = Path(root) if root else get_root()
    label = version_label(version)
    staged = _staged(version, utdq_net)
    entry = {"step": "merge", "date": datetime.datetime.now().isoformat(timespec="seconds"), "commit": _commit(),
             "root": str(root), "mode": "replace" if utdq_net in REPLACE else "append"}
    if not staged["events"].exists() or not staged["picks"].exists():
        entry.update({"merged_events": 0, "note": "nothing staged (no new events with picks)"})
        _log(version, utdq_net, entry)
        return entry
    paths = {k: root / get_hf_entry(k).path.format(utdq_net=utdq_net) for k in ("events", "picks", "stations")}
    backups = root / ".utdquake" / "backups" / f"{version}_merge"
    old = {k: pd.read_parquet(p) if p.exists() else None for k, p in paths.items()}
    new = {k: pd.read_parquet(p) for k, p in staged.items()}
    # columns and dtypes of the tables: the network's, or for a new network its template's
    ref = dict(old)
    if old["events"] is None and utdq_net in NEW_NETWORK_INFO:
        tmpl = NEW_NETWORK_INFO[utdq_net]["template"]
        ref = {k: pd.read_parquet(root / get_hf_entry(k).path.format(utdq_net=tmpl)) for k in paths}

    ev, pk, st = new["events"], new["picks"], new["stations"]
    n_staged = len(ev)
    ev = ev[ev["event_id"].isin(pk["event_id"])].drop_duplicates("event_id")
    n_with_picks = len(ev)
    if entry["mode"] == "append" and old["events"] is not None:
        ev = ev[~ev["event_id"].isin(old["events"]["event_id"])]
    pk = pk[pk["event_id"].isin(ev["event_id"])].drop_duplicates(["event_id", "pick_id"])
    ev, pk = ev.assign(dataset_version=label, utdq_net=utdq_net), pk.assign(dataset_version=label, utdq_net=utdq_net)
    st = st.assign(utdq_net=utdq_net)
    st["db_path"] = utdq_net + "/.stations/." + st["network"].astype(str) + "_" + st["station"].astype(str) + ".db"
    if old["stations"] is not None:
        have = set(zip(old["stations"]["network"].astype(str), old["stations"]["station"].astype(str)))
        st = st[[(n, s) not in have for n, s in zip(st["network"].astype(str), st["station"].astype(str))]]
    st = st.drop_duplicates(["network", "station"])

    if entry["mode"] == "replace" or old["events"] is None:
        events, picks = _ns(ev), _ns(pk)
        if ref["events"] is not None:
            events, picks = _like(events, ref["events"]), _like(picks, ref["picks"])
    else:
        events = pd.concat([old["events"], _like(ev, old["events"])], ignore_index=True)
        picks = pd.concat([old["picks"], _like(pk, old["picks"])], ignore_index=True)
    if old["stations"] is not None:
        stations = pd.concat([old["stations"], _like(st, old["stations"])], ignore_index=True)
    else:
        stations = _like(st, ref["stations"]) if ref["stations"] is not None else _ns(st)
    events = events.sort_values("time", kind="stable", ignore_index=True)
    assert not events["event_id"].duplicated().any(), "duplicated event ids after the merge"
    assert picks["event_id"].isin(events["event_id"]).all(), "picks of events not in the table"

    # network table row: counts of the merged tables
    npath = root / get_hf_entry("networks").path
    table = pd.read_parquet(npath)
    if utdq_net not in set(table["utdq_net"]):
        info = NEW_NETWORK_INFO.get(utdq_net)
        if info is None:
            raise ValueError(f"{utdq_net} is not in the network table: add it to NEW_NETWORK_INFO")
        row = table[table["utdq_net"] == info["template"]].copy()
        row["utdq_net"], row["dataset_version"] = utdq_net, label
        for k, v in info.items():
            if k != "template":
                row[k] = v
        for c in ("original_events", "original_p_arrivals", "original_s_arrivals", "last_published"):
            row[c] = pd.NA
        table = pd.concat([table, row], ignore_index=True)
    summary = get_network_summary(stations=stations, events=events, picks=picks)
    i = table.index[table["utdq_net"] == utdq_net][0]
    before = {k: table.at[i, k] for k in ("events", "p_arrivals", "s_arrivals", "total_stations")}
    for k in _NETWORK_COUNTS:
        if k in summary:
            table.at[i, k] = summary[k]
    by_net = picks.groupby("network").size().sort_values(ascending=False, kind="stable")
    table.at[i, "networks"] = ",".join(map(str, by_net.index))

    _write(events, paths["events"], backups / "events" / paths["events"].name)
    _write(picks, paths["picks"], backups / "picks" / paths["picks"].name)
    _write(stations, paths["stations"], backups / "stations" / paths["stations"].name)
    _write(table, npath, backups / "network" / f"network_before_{utdq_net}.parquet")
    entry.update({"staged_events": n_staged, "staged_with_picks": n_with_picks, "merged_events": len(ev),
                  "merged_picks": len(pk), "new_stations": len(st), "events": len(events), "picks": len(picks),
                  "stations": len(stations), "network_before": {k: str(v) for k, v in before.items()},
                  "network_after": {k: str(table.at[i, k]) for k in before}})
    _log(version, utdq_net, entry)
    logger.info("%s merged: %s", utdq_net, entry)
    return entry


# ----------------------------------------------------------------------------------------------------------
# Fixes after the merge. v1 lost every pick whose phase was not one of TravelTime.DEFAULT_PHASES (exact case:
# PG, SG, PN, SN, ...) when build_travel_time_model rewrote the picks table; the events whose picks were all
# like that were left without picks (HEL, OTT). restore_v1_picks processes those v1 events again from the v1
# bank, normalize_phases writes the regional phases as Pg/Pn/Sg/Sn (as in v1) and recounts them.

#: Regional phases written in the case of TravelTime.DEFAULT_PHASES, by their upper-case code.
PHASE_CASE = {p.upper(): p for p in ("Pg", "Pn", "Sg", "Sn")}
#: Event-table columns: the number of picks of each phase (exact phase code).
PHASE_COUNTS = {"P": "p_count", "Pg": "pg_count", "Pn": "pn_count", "S": "s_count", "Sg": "sg_count",
                "Sn": "sn_count"}


def _tables(root: Path, utdq_net: str) -> dict:
    return {k: root / get_hf_entry(k).path.format(utdq_net=utdq_net) for k in ("events", "picks", "stations")}


def _network_counts(root: Path, utdq_net: str, events, picks, stations) -> tuple:
    """The network table with the counts of ``utdq_net`` recomputed, and the counts before."""
    from utdquake.utils.utils import get_network_summary
    npath = root / get_hf_entry("networks").path
    table = pd.read_parquet(npath)
    summary = get_network_summary(stations=stations, events=events, picks=picks)
    i = table.index[table["utdq_net"] == utdq_net][0]
    before = {k: str(table.at[i, k]) for k in ("events", "p_arrivals", "s_arrivals", "pg_count", "sg_count")}
    for k in _NETWORK_COUNTS:
        if k in summary:
            table.at[i, k] = summary[k]
    by_net = picks.groupby("network").size().sort_values(ascending=False, kind="stable")
    table.at[i, "networks"] = ",".join(map(str, by_net.index))
    after = {k: str(table.at[i, k]) for k in before}
    return table, npath, before, after


def _recount(events: pd.DataFrame, picks: pd.DataFrame) -> pd.DataFrame:
    """The PHASE_COUNTS columns of ``events`` from ``picks``."""
    events = events.copy()
    for phase, col in PHASE_COUNTS.items():
        if col in events:
            n = picks[picks["phase"] == phase].groupby("event_id").size()
            events[col] = events["event_id"].map(n).fillna(0).astype(events[col].dtype)
    return events


def normalize_phases(version: str, utdq_net: str, root=None) -> dict:
    """Write the regional phases of a network's picks as Pg/Pn/Sg/Sn (PG -> Pg, ...), recount the events'
    PHASE_COUNTS and the network-table counts. Backups in ``<root>/.utdquake/backups/<version>_fix/``."""
    root = Path(root) if root else get_root()
    paths = _tables(root, utdq_net)
    backups = root / ".utdquake" / "backups" / f"{version}_fix"
    pk = pd.read_parquet(paths["picks"])
    phase = pk["phase"].astype("string")
    new = phase.str.upper().map(PHASE_CASE).fillna(phase)
    changed = phase.ne(new).fillna(False)
    entry = {"step": "normalize_phases", "date": datetime.datetime.now().isoformat(timespec="seconds"),
             "commit": _commit(), "root": str(root), "renamed": int(changed.sum()),
             "by_phase": phase[changed].value_counts().to_dict()}
    if changed.any():
        pk["phase"] = new.astype(pk["phase"].dtype)
        ev, st = pd.read_parquet(paths["events"]), pd.read_parquet(paths["stations"])
        ev = _recount(ev, pk)
        table, npath, entry["network_before"], entry["network_after"] = _network_counts(root, utdq_net, ev, pk, st)
        _write(pk, paths["picks"], backups / "picks" / paths["picks"].name)
        _write(ev, paths["events"], backups / "events" / paths["events"].name)
        _write(table, npath, backups / "network" / f"network_before_phases_{utdq_net}.parquet")
    _log(version, utdq_net, entry)
    logger.info("%s phases: %s", utdq_net, entry)
    return entry


def restore_v1_picks(version: str, utdq_net: str, root=None) -> dict:
    """The v1 events of a network without picks, processed again from the v1 bank (``<root>/banks/<net>``) as
    the new events are (:func:`stage`, as ``<net>_v1fix``); their event rows are replaced, their picks and new
    stations added, all with ``dataset_version`` v1. Backups in ``<root>/.utdquake/backups/<version>_fix/``."""
    import shutil
    root = Path(root) if root else get_root()
    paths = _tables(root, utdq_net)
    backups = root / ".utdquake" / "backups" / f"{version}_fix"
    ev, pk, st = (pd.read_parquet(paths[k]) for k in ("events", "picks", "stations"))
    lost = ev[(ev["dataset_version"] == "v1") & ~ev["event_id"].isin(pk["event_id"])]["event_id"]
    entry = {"step": "restore_v1_picks", "date": datetime.datetime.now().isoformat(timespec="seconds"),
             "commit": _commit(), "root": str(root), "v1_without_picks": len(lost)}
    if lost.empty:
        _log(version, utdq_net, entry)
        return entry
    # the lost events' QuakeML files, copied from the v1 bank into a bank of their own
    fix = f"{utdq_net}_v1fix"
    src = obsplus.EventBank(str(root / "banks" / utdq_net))
    index = src.read_index()
    files = index[index["event_id"].astype(str).isin(set(lost))]["path"]
    dst = work_dir(version) / "banks" / fix
    for rel in files:
        target = dst / rel.lstrip("/")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(Path(src.bank_path) / rel.lstrip("/"), target)
    _bank(dst).update_index()
    entry["files"] = len(files)
    entry["stage"] = stage(version, fix)
    staged = {k: pd.read_parquet(p) for k, p in _staged(version, fix).items()}
    sev, spk, sst = staged["events"], staged["picks"], staged["stations"]
    sev = sev[sev["event_id"].isin(spk["event_id"]) & sev["event_id"].isin(lost)].drop_duplicates("event_id")
    spk = spk[spk["event_id"].isin(sev["event_id"])].drop_duplicates(["event_id", "pick_id"])
    sev = sev.assign(dataset_version="v1", utdq_net=utdq_net)
    spk = spk.assign(dataset_version="v1", utdq_net=utdq_net)
    sst = sst.assign(utdq_net=utdq_net)
    if "dataset_version" in sst:
        sst["dataset_version"] = "v1"
    sst["db_path"] = utdq_net + "/.stations/." + sst["network"].astype(str) + "_" + sst["station"].astype(str) + ".db"
    have = set(zip(st["network"].astype(str), st["station"].astype(str)))
    sst = sst[[(n, s) not in have for n, s in zip(sst["network"].astype(str), sst["station"].astype(str))]]
    sst = sst.drop_duplicates(["network", "station"])

    events = pd.concat([ev[~ev["event_id"].isin(sev["event_id"])], _like(sev, ev)], ignore_index=True)
    events = events.sort_values("time", kind="stable", ignore_index=True)
    picks = pd.concat([pk, _like(spk, pk)], ignore_index=True)
    stations = pd.concat([st, _like(sst, st)], ignore_index=True)
    assert len(events) == len(ev) and not events["event_id"].duplicated().any(), "events changed in number"
    assert picks["event_id"].isin(events["event_id"]).all(), "picks of events not in the table"
    table, npath, entry["network_before"], entry["network_after"] = _network_counts(root, utdq_net, events,
                                                                                   picks, stations)
    _write(events, paths["events"], backups / "events" / paths["events"].name)
    _write(picks, paths["picks"], backups / "picks" / paths["picks"].name)
    _write(stations, paths["stations"], backups / "stations" / paths["stations"].name)
    _write(table, npath, backups / "network" / f"network_before_restore_{utdq_net}.parquet")
    entry.update({"restored_events": len(sev), "still_without_picks": int(len(lost) - len(sev)),
                  "restored_picks": len(spk), "new_stations": len(sst), "events": len(events),
                  "picks": len(picks), "stations": len(stations)})
    _log(version, utdq_net, entry)
    logger.info("%s v1 picks restored: %s", utdq_net, entry)
    return entry


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m utdquake.extend", description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="step", required=True)
    r = sub.add_parser("recipe")
    r.add_argument("version")
    r.add_argument("--target", type=int, default=20000)
    r.add_argument("--end", default=None)
    r.add_argument("--extra", default=None, help="CSV of new networks (recipe columns)")
    d = sub.add_parser("download")
    d.add_argument("version")
    d.add_argument("utdq_net")
    d.add_argument("--workers", type=int, default=8)
    u = sub.add_parser("run")
    u.add_argument("version")
    u.add_argument("--provider", required=True)
    u.add_argument("--parallel", type=int, default=1, help="networks of each provider at a time")
    u.add_argument("--workers", type=int, default=2, help="ComCat phase-data requests at a time")
    u.add_argument("--hours", type=float, default=46)
    s = sub.add_parser("status")
    s.add_argument("version")
    for step in ("stations", "stage"):
        q = sub.add_parser(step)
        q.add_argument("version")
        q.add_argument("utdq_net")
    m = sub.add_parser("merge")
    m.add_argument("version")
    m.add_argument("utdq_net", nargs="+")
    m.add_argument("--root", default=None, help="root to merge into (default: the working copy)")
    for step in ("restore_v1_picks", "normalize_phases"):
        q = sub.add_parser(step)
        q.add_argument("version")
        q.add_argument("utdq_net", nargs="+")
        q.add_argument("--root", default=None)
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    if a.step == "recipe":
        extra = pd.read_csv(a.extra).to_dict("records") if a.extra else None
        print(make_recipe(a.version, a.target, a.end, extra).to_string(index=False))
    elif a.step == "download":
        print(json.dumps(download(a.version, a.utdq_net, a.workers), indent=1, default=str))
    elif a.step == "run":
        left = run(a.version, a.provider, a.parallel, a.workers, a.hours)
        print(f"still to download: {len(left)} {left}")
        raise SystemExit(3 if left else 0)
    elif a.step == "stations":
        print(stations(a.version, a.utdq_net).to_string(index=False))
    elif a.step == "stage":
        print(json.dumps(stage(a.version, a.utdq_net), indent=1, default=str))
    elif a.step == "merge":
        for net in a.utdq_net:
            print(json.dumps(merge(a.version, net, a.root), indent=1, default=str))
    elif a.step in ("restore_v1_picks", "normalize_phases"):
        fn = restore_v1_picks if a.step == "restore_v1_picks" else normalize_phases
        for net in a.utdq_net:
            print(json.dumps(fn(a.version, net, a.root), indent=1, default=str))
    else:
        print(status(a.version).to_string(index=False))


if __name__ == "__main__":
    main()
