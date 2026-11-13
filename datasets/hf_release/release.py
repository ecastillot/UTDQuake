"""Release a dataset version of UTDQuake (ecastillot/UTDQuake on the Hub) as ONE pull request, then tag it.

    python release.py VERSION check               # every network ready (tables, travel times, stats, figures,
                                                  #   required info, version labels); exit 1 if not
    python release.py VERSION zips NET [NET ...]  # banks/<net>.zip, as hub.publish_network makes them (SLURM)
    python release.py VERSION plan                # files that differ from main (sha256), sizes; nothing sent
    python release.py VERSION open                # pull request + the files in commits of ~BATCH_GB to it
    python release.py VERSION verify <pr>         # every planned file on the PR has the local sha256
    python release.py VERSION tag                 # after the PR is merged: tag VERSION on main (refuses
                                                  #   if it is not merged; a PR opens as a draft: mark it
                                                  #   ready, then merge, on the Hub or HfApi)

VERSION is the tag, e.g. v2.0 (a major release) or v2.1 (the next minor one). See docs/source/versions.rst:
"How versions work". Files, for every seismic UTDQuake network of the local network table ($UTDQUAKE_ROOT,
default UTDQuake): events, picks and stations tables, stats cache, travel-time model and bank zip, plus
network/network.parquet and the notes of NOTES (e.g. notes/R11_catalog_description.txt). Only files whose
content differs from main are sent; none is deleted. Zips are built once into
<root>/.utdquake/release_<VERSION>/ and reused (same bytes for plan/open/verify). The PR is merged after
review; then ``tag``.
"""
import hashlib
import json
import os
import sys
import zipfile
from pathlib import Path

import pandas as pd

REPO, TYPE = "ecastillot/UTDQuake", "dataset"
ROOT = Path(os.environ.get("UTDQUAKE_ROOT", "/groups/igonin/ecastillo/UTDQuake"))
TAG = sys.argv[1] if len(sys.argv) > 1 else "v2.0"
STAGE = ROOT / ".utdquake" / f"release_{TAG}"
TITLE = f"Dataset {TAG}"
N_FIGURES = 9            # figures generate_network_figures makes per network
BATCH_GB = 4.0
FILES = ["events/utdq_net={}.parquet", "picks/utdq_net={}.parquet", "stations/utdq_net={}.parquet",
         ".utdquake/stats/{}.npz", ".utdquake/travel_time/{}.parquet", "banks/{}.zip"]
TABLE = "network/network.parquet"
NOTES = {"notes/R11_catalog_description.txt": ROOT / "figures" / "networks" / "R11" / "R11_catalog_description.txt"}
DESCRIPTIONS = {"v2.0": """UTDQuake dataset v2.0: agency networks extended to up to 20,000 events after QC (new events
labelled v2), JMA rebuilt with its S picks, new networks ci, R09, R10 and R11 (synthetic), ISC IR stations
resolved, phase labels Pg/Pn/Sg/Sn, v1 picks restored (HEL, OTT), banks with the new events.
See docs/source/versions.rst.""",
                "v2.1": """UTDQuake v2.1 (in preparation), corrections to v2.0 data: 13 events with impossible depths removed
with their 201 picks (default 700/750 km depths, one 9,330 km origin: NOA, TUN, PRE, NOU, MDD, JSN, TIR), 2 uw
placeholder magnitudes (-5.0) emptied, R08 continent World; updated R11 description (R03 reference).
See docs/source/versions.rst, v2.1.""",
                "v2.2": """UTDQuake dataset v2.2: two new research networks in Antarctica, the first in UTDQuake (Ho et al.,
Zenodo, CC BY 4.0): R12 East Antarctica (Victoria Land, Transantarctic Mountains; 776 events 2001-2015, crustal and
upper-mantle earthquakes, 11,620 picks, 50 stations; doi 10.5281/zenodo.17519077) and R13 West Antarctica (Pine Island
Glacier; 1,002 events in 2016, 9,916 picks, 8 stations; doi 10.5281/zenodo.20128910). No other network changes.
See docs/source/versions.rst, v2.2."""}
DESCRIPTION = DESCRIPTIONS.get(TAG, f"UTDQuake dataset {TAG}. See docs/source/versions.rst.")


def api():
    from huggingface_hub import HfApi
    return HfApi(token=os.environ.get("HF_TOKEN"))


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def bank_zip(net: str) -> Path:
    """<STAGE>/banks/<net>.zip: entries prefixed with ``<net>/`` (hub.publish_network's format), sorted, fixed
    timestamps so that rebuilding gives the same bytes."""
    out = STAGE / "banks" / f"{net}.zip"
    out.parent.mkdir(parents=True, exist_ok=True)
    bank = ROOT / "banks" / net
    tmp = out.with_suffix(".zip.tmp")
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(bank.rglob("*")):
            if f.is_file():
                info = zipfile.ZipInfo(str(f.relative_to(bank.parent)), date_time=(2026, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                zf.writestr(info, f.read_bytes())
    tmp.replace(out)
    return out


def networks() -> list:
    table = pd.read_parquet(ROOT / TABLE)
    return sorted(table["utdq_net"].astype(str))


def local_files() -> dict:
    """{path in repo: local path} of every file of the release."""
    out = {TABLE: ROOT / TABLE}
    for net in networks():
        for f in FILES:
            rel = f.format(net)
            src = STAGE / rel if rel.startswith("banks/") else ROOT / rel
            if src.exists():
                out[rel] = src
    out.update({k: v for k, v in NOTES.items() if v.exists()})
    return out


def remote(rev: str) -> dict:
    return {f.path: (f.lfs.sha256 if f.lfs else None)
            for f in api().list_repo_tree(REPO, repo_type=TYPE, revision=rev, recursive=True) if hasattr(f, "size")}


def plan(rev: str = "main") -> pd.DataFrame:
    files, rem = local_files(), remote(rev)
    rows = []
    for rel, src in sorted(files.items()):
        s = sha(src)
        rows.append({"path": rel, "local": str(src), "sha256": s, "bytes": src.stat().st_size,
                     "on_main": rel in rem, "changed": rem.get(rel) != s})
    df = pd.DataFrame(rows)
    df.to_csv(STAGE / "plan.csv", index=False)
    missing = [n for n in networks() if not (STAGE / f"banks/{n}.zip").exists()]
    print(f"{len(df)} files, {df.changed.sum()} to send ({df[df.changed].bytes.sum() / 1e9:.2f} GB), "
          f"{(~df.on_main).sum()} new; bank zips not built: {missing or 'none'}")
    return df


def check() -> bool:
    """Every network ready for the release; prints the problems."""
    from utdquake.writers.schema import missing_network_info
    table = pd.read_parquet(ROOT / TABLE)
    label = TAG.split(".")[0] if TAG.endswith(".0") else TAG          # v2.0 -> rows labelled v2; v2.1 -> v2.1
    allowed = {"v1", "v2"} | {label}
    problems = []
    for row in table.itertuples(index=False):
        net = str(row.utdq_net)
        p = [f"{c}" for c in missing_network_info(row._asdict())]
        for f in FILES[:5]:
            if not (ROOT / f.format(net)).exists():
                p.append(f"missing {f.format(net)}")
        if not (ROOT / "banks" / net).exists():
            p.append("missing bank")
        figs = list((ROOT / "figures" / "networks" / net).glob(f"{net}_*.png"))
        if len(figs) < N_FIGURES:
            p.append(f"{len(figs)} figures (< {N_FIGURES})")
        ev = ROOT / f"events/utdq_net={net}.parquet"
        if ev.exists():
            v = set(pd.read_parquet(ev, columns=["dataset_version"])["dataset_version"].dropna().astype(str))
            if v - allowed:
                p.append(f"dataset_version labels {sorted(v - allowed)} not in {sorted(allowed)}")
        if p:
            problems.append(f"{net}: " + "; ".join(p))
    print(f"{len(table)} networks checked for {TAG}: {len(problems)} with problems")
    for line in problems:
        print("  " + line)
    return not problems


def main():
    step = sys.argv[2]
    if step == "check":
        sys.exit(0 if check() else 1)
    elif step == "zips":
        for net in sys.argv[3:]:
            z = bank_zip(net)
            print(f"{net}: {z.stat().st_size / 1e6:.0f} MB", flush=True)
    elif step == "plan":
        plan()
    elif step == "open":
        from huggingface_hub import CommitOperationAdd
        if not check():
            sys.exit("not opening the pull request: fix the problems above first")
        df = plan()
        todo = df[df.changed]
        pr = api().create_pull_request(REPO, repo_type=TYPE, title=TITLE, description=DESCRIPTION)
        print(f"PR #{pr.num}: {pr.url}", flush=True)
        batch, size, n = [], 0, 0
        for r in todo.itertuples():
            batch.append(CommitOperationAdd(path_in_repo=r.path, path_or_fileobj=r.local))
            size += r.bytes
            if size > BATCH_GB * 1e9 or r.Index == todo.index[-1]:
                n += 1
                api().create_commit(REPO, repo_type=TYPE, operations=batch, revision=pr.git_reference,
                                    commit_message=f"{TITLE}: part {n} ({len(batch)} files)")
                print(f"part {n}: {len(batch)} files, {size / 1e9:.2f} GB", flush=True)
                batch, size = [], 0
        (STAGE / "pr.json").write_text(json.dumps({"num": pr.num, "url": pr.url, "parts": n}))
    elif step == "verify":
        num = int(sys.argv[3])
        df = pd.read_csv(STAGE / "plan.csv")
        rem = remote(f"refs/pr/{num}")
        missing = [r.path for r in df.itertuples() if r.path not in rem]
        wrong = [r.path for r in df.itertuples() if r.path in rem and rem[r.path] is not None and rem[r.path] != r.sha256]
        bad = missing + wrong
        small = [r.path for r in df.itertuples() if r.path in rem and rem[r.path] is None]
        print(f"PR #{num}: {len(df)} files checked; wrong or missing: {len(bad)} {bad[:10]}; "
              f"not LFS (not checked by sha): {len(small)}")
        sys.exit(1 if bad else 0)
    elif step == "tag":
        # only once the release PR is merged, and on the merged commit (a PR opens as a draft: merging a draft
        # fails, and tagging main before the merge would tag the previous data)
        num = json.loads((STAGE / "pr.json").read_text())["num"]
        if api().get_discussion_details(REPO, num, repo_type=TYPE).status != "merged":
            sys.exit(f"PR #{num} is not merged: not tagging")
        sha = api().dataset_info(REPO).sha
        api().create_tag(REPO, repo_type=TYPE, tag=TAG, revision=sha, tag_message=f"UTDQuake dataset {TAG}")
        print(f"tagged {TAG} on {sha}")


if __name__ == "__main__":
    main()
