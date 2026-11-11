"""Travel-time model (+ z-scores of all the picks, v1 included), stats cache and figures of merged networks.

    python tt_figures.py NET [NET ...]

Uses $UTDQUAKE_ROOT; figures into <root>/figures/networks/<net>. A failed network is reported and the next one
goes on; a line per network is appended to <root>/.utdquake/extend/v2.0/tt_figures.csv.
"""
import os, sys, time, traceback
from pathlib import Path
import pandas as pd
from utdquake import Network, generate_network_figures
from utdquake.qc.travel_time import build_travel_time_model

root = Path(os.environ["UTDQUAKE_ROOT"])
log = root / ".utdquake" / "extend" / "v2.0" / "tt_figures.csv"
failed = []
for net in sys.argv[1:]:
    t0, row = time.time(), {"utdq_net": net, "date": pd.Timestamp.now().isoformat(timespec="seconds")}
    try:
        if not os.environ.get("FIGURES_ONLY"):          # FIGURES_ONLY=1: stats and figures only
            print(f"== {net} travel time", flush=True)
            build_travel_time_model(net, local_root=root, update_picks=True)
        pk = pd.read_parquet(root / "picks" / f"utdq_net={net}.parquet", columns=["travel_time_zscore"])
        row.update(picks=len(pk), zscore_nan=int(pk.travel_time_zscore.isna().sum()))
        print(f"== {net} stats", flush=True)
        Network(net).compute_stats(use_cache=False)
        print(f"== {net} figures", flush=True)
        saved = generate_network_figures(net, outdir=root / "figures" / "networks" / net, das=False)
        row.update(figures=len(saved), status="ok")
    except Exception as e:
        traceback.print_exc()
        row.update(status=f"failed: {type(e).__name__}: {e}"[:300])
        failed.append(net)
    row["seconds"] = round(time.time() - t0)
    print(row, flush=True)
    pd.DataFrame([row]).to_csv(log, mode="a", header=not log.exists(), index=False)
print("failed:", failed or "none")
sys.exit(1 if failed else 0)
