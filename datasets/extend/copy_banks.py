"""Copy the staged QuakeML banks of the new events into the UTDQuake banks, then index and check them.

    python copy_banks.py VERSION NET [NET ...]

Per network: the staged bank (<root>/.utdquake/extend/<version>/stage/banks/<net>) is copied into
<root>/banks/<net> without overwriting a file already there (the v1 events stay as they are); networks of
extend.REPLACE (JMA) get the staged bank instead (the old one moved to .utdquake/backups/<version>_banks/).
Then the bank index is updated, and every event of the network's events table must be in it, once.
A line per network is appended to <root>/.utdquake/extend/<version>/copy_banks.csv.
"""
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import obsplus
import pandas as pd

from utdquake import extend as x

version, nets = sys.argv[1], sys.argv[2:]
root = Path(os.environ["UTDQUAKE_ROOT"])
work = root / ".utdquake" / "extend" / version
log = work / "copy_banks.csv"
failed = []
for net in nets:
    t0 = time.time()
    src, dst = work / "stage" / "banks" / net, root / "banks" / net
    row = {"utdq_net": net}
    try:
        if not src.exists():
            raise FileNotFoundError(src)
        if net in x.REPLACE and not (root / ".utdquake" / "backups" / f"{version}_banks" / net).exists():
            backup = root / ".utdquake" / "backups" / f"{version}_banks" / net
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(dst), str(backup))
            row["moved_old_bank_to"] = str(backup)
        dst.mkdir(parents=True, exist_ok=True)
        subprocess.run(["rsync", "-a", "--ignore-existing", "--exclude", ".index.db", "--exclude", ".*",
                        f"{src}/", f"{dst}/"], check=True)
        bank = obsplus.EventBank(str(dst))
        bank.update_index()
        index = bank.read_index()
        ids = index["event_id"].astype(str)
        events = pd.read_parquet(root / "events" / f"utdq_net={net}.parquet", columns=["event_id"])
        missing = int((~events["event_id"].isin(ids)).sum())
        dup = int(ids.duplicated().sum())
        row.update(bank_events=len(index), table_events=len(events), table_events_not_in_bank=missing,
                   duplicated_ids=dup, status="ok" if missing == 0 and dup == 0 else "check")
        if row["status"] != "ok":
            failed.append(net)
    except Exception as e:
        row["status"] = f"failed: {type(e).__name__}: {e}"[:300]
        failed.append(net)
    row["seconds"] = round(time.time() - t0)
    print(row, flush=True)
    pd.DataFrame([row]).to_csv(log, mode="a", header=not log.exists(), index=False)
print("failed / to check:", failed or "none")
sys.exit(1 if failed else 0)
