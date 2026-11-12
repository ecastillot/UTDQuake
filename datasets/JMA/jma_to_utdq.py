"""JMA (Japan Meteorological Agency) events for the UTDQuake v2.0 extension.

Source: The Seismological Bulletin of Japan, "1.3 Earthquake data" (the source of the v1 JMA events):
https://www.data.jma.go.jp/eqev/data/bulletin/eqdoc_e.html, one zip per month,
https://www.data.jma.go.jp/eqev/data/bulletin/catalog/table3/dYYYYMMt.zip (text, 1997-10 onwards).

Each event: a header (origin time and error, region, LAT/LONG/DEPTH with errors, MAG1) and one line per station
with its P and S arrival times (``EP``/``IP``/``P``, ``ES``/``IS``/``S``), then a dashed end line. Read as in v1:
network ``JAPAN``, station codes with ``.`` replaced by ``-`` (v1: ``N.TSOH`` -> ``N-TSOH``), location and instrument
``--``, event id ``smi:local/<origin time YYYYmmddHHMMSSffffff>``.

Kept with their JMA label as an event comment: ``POOR SOLUTION`` and ``AFTER USGS`` (hypocentre after the
USGS) events, as in v1. Not kept: matched-filter events (``MF``: their ``X`` times come from a template, not picks; v1 left them out),
amplitude-only lines (``M``), events without a location or without picks. A pick time is the origin date plus the
pick's clock time, moved by a day only when they are more than 12 h apart (midnight); v1 added a day to every pick
slightly before the origin (travel time 86,399.8 s). Each arrival carries the station's distance and azimuth (DELTA,
AZM): UTDQuake calculates from them the positions of the stations it has no coordinates of (151 JMA stations of
March-April 2023 are in no station service), as in v1; without them the station step dropped 257 events.

The events after the last v1 event, up to the extension cap, are written to the extension bank of JMA
(``<root>/.utdquake/extend/v2.0/banks/JMA``, as the FDSN downloads), with a download entry in ``JMA.json``; the
stations/stage/merge steps of ``utdquake.extend`` take them from there.

The v1 events themselves are rebuilt too (``replace-v1``): the v1 converter read only the first phase column of a
station line, so it kept an S pick only where a station had no P (19K S picks against 66K in the bulletin for the
same 4,918 events). The v1 events, with their v1 ids and the same origins and magnitudes, are written with all their
P and S picks to a separate bank, ``banks/JMA_v1``: the merge replaces the v1 rows of JMA with them (the only network
whose v1 rows are rebuilt; user, 2026-11-07: "the idea is to have the data complete").

    python jma_to_utdq.py compare 2023-03        # parse a month and compare 1-9 March with v1
    python jma_to_utdq.py extend                 # write the new events to the extension bank
    python jma_to_utdq.py replace-v1             # the v1 events with all their picks, to banks/JMA_v1
    python jma_to_utdq.py combine                # banks/JMA_v1 into the JMA bank (JMA is staged as one set)
    sbatch run_jma_rebuild.sh                    # all of it from scratch, then the stage step
"""
import argparse
import datetime
import io
import json
import logging
import math
import os
import re
import urllib.request
import zipfile
from pathlib import Path

import pandas as pd

logger = logging.getLogger("jma_to_utdq")
HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
URL = "https://www.data.jma.go.jp/eqev/data/bulletin/catalog/table3/d{ym}t.zip"
UTDQ_NET, NETWORK, AGENCY = "JMA", "JAPAN", "JMA"
VERSION = "v2.0"

HEADER = re.compile(r"^(?P<label>[A-Z][A-Z ]*?)?\s+(?P<Y>\d{4})Y\s+(?P<M>\d+)M\s+(?P<D>\d+)D\s+(?P<h>\d+)H\s+(?P<m>\d+)M\s+"
                    r"(?P<s>[\d.]+)S\s+(?:\+/-\s*(?P<terr>[\d.]+))?\s*(?P<region>.*?)\s+R=")
LOCATION = re.compile(r"LAT=\s*(?P<latd>\d+)\s+(?P<latm>[\d.]+)(?P<ns>[NS])\s*(?:\+/-\s*(?P<laterr>[\d.]+))?\s+"
                      r"LONG=\s*(?P<lond>\d+)\s+(?P<lonm>[\d.]+)(?P<ew>[EW])\s*(?:\+/-\s*(?P<lonerr>[\d.]+))?\s+"
                      r"DEPTH=\s*(?P<dep>-?[\d.]+)KM\s*(?:\+/-\s*(?P<deperr>[\d.]+))?"
                      r"(?:.*?MAG1=\s*(?P<mag>-?[\d.]+)(?P<magtype>[A-Za-z]?))?")
P_PHASES, S_PHASES = {"P", "EP", "IP"}, {"S", "ES", "IS"}
KM_PER_DEGREE = 111.195


def month_text(ym: str) -> str:
    """The text of one month (cached in raw/)."""
    RAW.mkdir(parents=True, exist_ok=True)
    path = RAW / f"d{ym}t.zip"
    if not path.exists():
        logger.info("downloading %s", URL.format(ym=ym))
        with urllib.request.urlopen(URL.format(ym=ym), timeout=300) as r:
            path.write_bytes(r.read())
    with zipfile.ZipFile(path) as z:
        return "".join(z.read(n).decode("latin-1") for n in sorted(z.namelist()) if n.endswith(".txt"))


def _clock(text: str):
    """'HH MM SS.SS' or 'MM SS.SS' -> (hour or None, minute, second)."""
    parts = text.split()
    if len(parts) == 3:
        return int(parts[0]), int(parts[1]), float(parts[2])
    if len(parts) == 2:
        return None, int(parts[0]), float(parts[1])
    raise ValueError(text)


def _at(origin: datetime.datetime, h: int, m: int, s: float) -> datetime.datetime:
    """Origin date + clock time, moved by a day only across midnight (more than 12 h from the origin)."""
    t = datetime.datetime(origin.year, origin.month, origin.day) + datetime.timedelta(hours=h, minutes=m, seconds=s)
    if (t - origin).total_seconds() > 43200:
        t -= datetime.timedelta(days=1)
    elif (t - origin).total_seconds() < -43200:
        t += datetime.timedelta(days=1)
    return t


def _delta_azimuth(line: str):
    """Epicentral distance (km) and azimuth (degrees) of a station line (columns DELTA and AZM), or Nones."""
    t = line[86:104].split()
    try:
        return float(t[0]), float(t[1])
    except (IndexError, ValueError):
        return None, None


def _phase_line(line: str, origin: datetime.datetime):
    """Picks of one station line: [(station, phase, time, distance km, azimuth)]. Columns as under the
    STATION/PHA/TIME/.../DELTA/AZM header."""
    station = line[0:9].strip().replace(".", "-")
    dist, azm = _delta_azimuth(line)
    ph1, t1 = line[9:14].strip(), line[14:26]
    ph2, t2 = line[32:37].strip(), line[37:45]
    out, hour1, minute1 = [], None, None
    if ph1 in P_PHASES | S_PHASES and t1.strip():
        hour1, minute1, sec = _clock(t1)
        if hour1 is None:
            return out
        out.append((station, "P" if ph1 in P_PHASES else "S", _at(origin, hour1, minute1, sec), dist, azm))
    if ph2 in S_PHASES and t2.strip() and hour1 is not None:
        h, m, s = _clock(t2)
        h = hour1 + (1 if m < minute1 else 0) if h is None else h  # S time has no hour: the P line's
        out.append((station, "S", _at(origin, h % 24, m, s), dist, azm))  # _at moves it across midnight
    return out


def parse(text: str):
    """Events and picks of a bulletin text: (events DataFrame, picks DataFrame, counts of what was left out)."""
    events, picks = [], []
    skipped = {"matched_filter": 0, "no_location": 0, "no_picks": 0}
    blocks = re.split(r"^-{20,}\s*$", text, flags=re.M)
    for block in blocks:
        lines = block.strip("\n").splitlines()
        head = next((i for i, l in enumerate(lines) if HEADER.match(l)), None)
        if head is None:
            continue
        h = HEADER.match(lines[head])
        label = (h["label"] or "").strip()
        if label == "MF":
            skipped["matched_filter"] += 1
            continue
        loc = LOCATION.search(lines[head + 1]) if head + 1 < len(lines) else None
        if loc is None:
            skipped["no_location"] += 1
            continue
        sec = float(h["s"])
        origin = datetime.datetime(int(h["Y"]), int(h["M"]), int(h["D"]), int(h["h"]), int(h["m"])) + \
            datetime.timedelta(seconds=sec)
        lat = (int(loc["latd"]) + float(loc["latm"]) / 60) * (1 if loc["ns"] == "N" else -1)
        lon = (int(loc["lond"]) + float(loc["lonm"]) / 60) * (1 if loc["ew"] == "E" else -1)
        event_id = "smi:local/" + origin.strftime("%Y%m%d%H%M%S%f")
        ev_picks = []
        start = next((i for i, l in enumerate(lines) if l.startswith("STATION")), None)
        for line in lines[start + 1:] if start is not None else []:
            if not line.strip() or line.startswith(("REMARK", " ")):
                continue
            try:
                ev_picks += _phase_line(line, origin)
            except ValueError:
                logger.debug("unreadable line in %s: %r", event_id, line)
        # one pick per station and phase (the first)
        seen, kept = set(), []
        for p in ev_picks:
            if p[:2] not in seen:
                seen.add(p[:2])
                kept.append(p)
        if not kept:
            skipped["no_picks"] += 1
            continue
        events.append({
            "event_id": event_id, "origin_time": origin, "latitude": lat, "longitude": lon,
            "depth[km]": float(loc["dep"]),
            "depth_error[km]": float(loc["deperr"]) if loc["deperr"] else None,
            "latitude_error": float(loc["laterr"]) / 60 if loc["laterr"] else None,  # minutes -> degrees
            "longitude_error": float(loc["lonerr"]) / 60 if loc["lonerr"] else None,
            "time_error": float(h["terr"]) if h["terr"] else None,
            "magnitude": float(loc["mag"]) if loc["mag"] else None, "magnitude_code": loc["magtype"] or None,
            "region": h["region"].strip(), "label": label or None, "agency": AGENCY})
        picks += [{"event_id": event_id, "network": NETWORK, "station": s, "location": "--",
                   "instrument_type": "--", "phase": ph, "pick_time": t, "distance_km": d, "azimuth": a,
                   "agency": AGENCY} for s, ph, t, d, a in kept]
    return pd.DataFrame(events), pd.DataFrame(picks), skipped


def build_catalog(events: pd.DataFrame, picks: pd.DataFrame):
    """ObsPy events (as v1: origin from get_origin, picks/arrivals from get_picks, magnitude type M)."""
    from obspy import UTCDateTime
    from obspy.core.event import (Catalog, Comment, CreationInfo, Event, EventDescription, QuantityError,
                                  ResourceIdentifier)
    from utdquake.bank.utils import get_magnitude, get_origin, get_picks

    by_event = dict(tuple(picks.groupby("event_id")))
    out = []
    for _, row in events.iterrows():
        rows = by_event[row["event_id"]]
        ev_picks = get_picks(rows)
        origin = get_origin(row, ev_picks)
        # the bulletin's distance and azimuth of each station: UTDQuake calculates the positions of stations
        # it has no coordinates of from them (as v1)
        for arrival, (_, p) in zip(origin.arrivals, rows.iterrows()):
            if pd.notna(p["distance_km"]) and pd.notna(p["azimuth"]):
                arrival.distance = float(p["distance_km"]) / KM_PER_DEGREE
                arrival.azimuth = float(p["azimuth"])
        if pd.notna(row["time_error"]):
            origin.time_errors = QuantityError(uncertainty=float(row["time_error"]))
        ev = Event(resource_id=ResourceIdentifier(id=row["event_id"]), event_type="earthquake", picks=ev_picks,
                   origins=[origin], event_descriptions=[EventDescription(text=row["region"], type="region name")],
                   comments=[Comment(text=f"JMA: {row['label']}")] if pd.notna(row["label"]) else [],
                   creation_info=CreationInfo(author=AGENCY, agency_id=AGENCY, creation_time=UTCDateTime.now()))
        ev.preferred_origin_id = origin.resource_id.id
        if pd.notna(row["magnitude"]):
            mag = get_magnitude(value=row["magnitude"], mag_type="M", evaluation_mode="manual",
                                evaluation_status="reviewed", agency=AGENCY, origin_id=origin.resource_id)
            ev.magnitudes = [mag]
            ev.preferred_magnitude_id = mag.resource_id.id
        out.append(ev)
    return Catalog(events=out)


def _months(start: str):
    y, m = int(start[:4]), int(start[4:])
    while True:
        yield f"{y:04d}{m:02d}"
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


def compare(ym: str) -> None:
    """Parse a month and compare its events up to the last v1 event with the v1 JMA events."""
    from utdquake.core.config import get_root
    ev, pk, skipped = parse(month_text(ym))
    v1 = pd.read_parquet(get_root() / "events" / f"utdq_net={UTDQ_NET}.parquet")
    v1p = pd.read_parquet(get_root() / "picks" / f"utdq_net={UTDQ_NET}.parquet", columns=["event_id", "phase"])
    last = pd.to_datetime(v1["time"]).max()
    part = ev[ev["origin_time"] <= last]
    print(f"{ym}: {len(ev)} events, {len(pk)} picks; left out {skipped}")
    print(f"up to the last v1 event ({last}): {len(part)} parsed, {len(v1)} in v1")
    m = part.merge(v1, on="event_id", how="inner", suffixes=("", "_v1"))
    print(f"same event id: {len(m)} of {len(v1)} v1 events")
    for a, b, scale in [("latitude", "latitude_v1", 1), ("longitude", "longitude_v1", 1),
                        ("depth[km]", "depth", 1e-3), ("magnitude", "magnitude_v1", 1)]:
        d = (m[a] - m[b] * scale).abs()
        print(f"  {a:10s} max |diff| {d.max():.6f}, equal (1e-4) {int((d < 1e-4).sum())}")
    n_new = pk[pk["event_id"].isin(m["event_id"])].groupby("event_id").size()
    n_v1 = v1p[v1p["event_id"].isin(m["event_id"])].groupby("event_id").size()
    j = pd.concat([n_new.rename("parsed"), n_v1.rename("v1")], axis=1).fillna(0)
    print(f"  picks per event: parsed {j.parsed.sum():.0f}, v1 (after QC) {j.v1.sum():.0f}; "
          f"events with more picks in v1 {int((j.v1 > j.parsed).sum())}")


def extend(target: int = 20000, margin: float = 1.05, chunk: int = 500) -> dict:
    """The events after the last v1 event, up to the cap, into the extension bank of JMA."""
    import obsplus
    from utdquake.core.config import get_root
    from utdquake.extend import NAME_STRUCTURE, PATH_STRUCTURE, _log, existing, work_dir

    old = existing(UTDQ_NET)
    cap = math.ceil(target * margin)
    bank_path = work_dir(VERSION) / "banks" / UTDQ_NET
    bank_path.mkdir(parents=True, exist_ok=True)
    bank = obsplus.EventBank(base_path=bank_path, path_structure=PATH_STRUCTURE, name_structure=NAME_STRUCTURE,
                             format="quakeml")
    bank.update_index()
    index = bank.read_index()
    have = set(index["event_id"]) if len(index) else set()
    after = pd.Timestamp(old["last"])
    entry = {"step": "download", "date": datetime.datetime.now().isoformat(timespec="seconds"),
             "provider": "JMA", "source": URL, "existing": old, "cap": cap, "months": [], "skipped": {}}
    remaining = cap - old["events"] - len(have)
    for ym in _months(after.strftime("%Y%m")):
        if remaining <= 0:
            break
        try:
            text = month_text(ym)
        except Exception as e:  # not published yet
            entry["error"] = f"{ym}: {type(e).__name__}: {e}"
            logger.warning(entry["error"])
            break
        ev, pk, skipped = parse(text)
        for k, v in skipped.items():
            entry["skipped"][k] = entry["skipped"].get(k, 0) + v
        ev = ev[(ev["origin_time"] > after) & ~ev["event_id"].isin(have)].sort_values("origin_time")
        ev = ev.drop_duplicates("event_id").head(remaining)
        for i in range(0, len(ev), chunk):
            part = ev.iloc[i:i + chunk]
            bank.put_events(build_catalog(part, pk[pk["event_id"].isin(part["event_id"])]))
        remaining -= len(ev)
        entry["months"].append({"month": ym, "new_events": len(ev)})
        logger.info("%s: %d new events (remaining %d)", ym, len(ev), remaining)
    entry["new_events"] = len(bank.read_index())
    entry["total"] = old["events"] + entry["new_events"]
    entry["complete"] = entry["total"] >= cap or "error" in entry
    _log(VERSION, UTDQ_NET, entry)
    return entry


def replace_v1(chunk: int = 500) -> dict:
    """The v1 JMA events, rebuilt from the bulletin with all their picks, into ``banks/JMA_v1``."""
    import obsplus
    from utdquake.core.config import get_root
    from utdquake.extend import NAME_STRUCTURE, PATH_STRUCTURE, _log, work_dir

    v1 = pd.read_parquet(get_root() / "events" / f"utdq_net={UTDQ_NET}.parquet", columns=["event_id", "time"])
    months = sorted(set(pd.to_datetime(v1["time"]).dt.strftime("%Y%m")))
    bank_path = work_dir(VERSION) / "banks" / f"{UTDQ_NET}_v1"
    bank_path.mkdir(parents=True, exist_ok=True)
    bank = obsplus.EventBank(base_path=bank_path, path_structure=PATH_STRUCTURE, name_structure=NAME_STRUCTURE,
                             format="quakeml")
    bank.update_index()
    index = bank.read_index()
    have = set(index["event_id"]) if len(index) else set()
    found = []
    for ym in months:
        ev, pk, _ = parse(month_text(ym))
        ev = ev[ev["event_id"].isin(v1["event_id"]) & ~ev["event_id"].isin(have)]
        found += list(ev["event_id"])
        for i in range(0, len(ev), chunk):
            part = ev.iloc[i:i + chunk]
            bank.put_events(build_catalog(part, pk[pk["event_id"].isin(part["event_id"])]))
    index = bank.read_index()
    missing = sorted(set(v1["event_id"]) - set(index["event_id"]))
    entry = {"step": "replace_v1", "date": datetime.datetime.now().isoformat(timespec="seconds"),
             "source": URL, "v1_events": len(v1), "rebuilt": len(index), "missing": missing[:20],
             "n_missing": len(missing), "bank": str(bank_path)}
    _log(VERSION, UTDQ_NET, entry)
    return entry


def combine() -> dict:
    """The rebuilt v1 events (``banks/JMA_v1``) into the JMA bank, so JMA is staged as one set of events."""
    import obsplus
    from utdquake.extend import _bank, _log, work_dir
    src = obsplus.EventBank(work_dir(VERSION) / "banks" / f"{UTDQ_NET}_v1")
    dst = _bank(work_dir(VERSION) / "banks" / UTDQ_NET)
    dst.update_index()
    have = set(dst.read_index()["event_id"])
    ids = [i for i in src.read_index()["event_id"] if i not in have]
    for i in range(0, len(ids), 500):
        dst.put_events(src.get_events(event_id=ids[i:i + 500]))
    index = dst.read_index()
    entry = {"step": "combine", "date": datetime.datetime.now().isoformat(timespec="seconds"), "added": len(ids),
             "events": len(index), "duplicated": int(index["event_id"].duplicated().sum())}
    _log(VERSION, UTDQ_NET, entry)
    return entry


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("compare")
    c.add_argument("month", help="YYYY-MM")
    sub.add_parser("extend")
    sub.add_parser("replace-v1")
    sub.add_parser("combine")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    os.environ.setdefault("UTDQUAKE_ROOT", "/groups/igonin/ecastillo/UTDQuake")
    if a.cmd == "compare":
        compare(a.month.replace("-", ""))
    elif a.cmd == "combine":
        print(json.dumps(combine(), indent=1, default=str))
    elif a.cmd == "replace-v1":
        print(json.dumps(replace_v1(), indent=1, default=str))
    else:
        print(json.dumps(extend(), indent=1, default=str))


if __name__ == "__main__":
    main()
