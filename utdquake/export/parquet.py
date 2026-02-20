import logging
import sqlite3
import pandas as pd
from pathlib import Path
from typing import Iterable, List

from .config import (PREF_PICKS_ORDER,
                      PREF_PICKS_TYPES,
                      PREF_EVENTS_ORDER,
                      PREF_EVENTS_TYPES,
                      sanitize_dataframe_for_parquet)


logger = logging.getLogger(__name__)

class ParquetExportProgress:
    """
    Tracks exported event_ids to allow resume-safe parquet export.

    Each processed event_id is marked as 'done'.
    """

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self._init_db()

    def _init_db(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS progress (
                    event_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    def is_done(self, event_id: str) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                "SELECT status FROM progress WHERE event_id=?",
                (event_id,),
            )
            row = cur.fetchone()
        return row is not None and row[0] == "done"

    def mark_done(self, event_id: str) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO progress (event_id, status)
                VALUES (?, 'done')
                ON CONFLICT(event_id)
                DO UPDATE SET status='done',
                              updated_at=CURRENT_TIMESTAMP
                """,
                (event_id,),
            )

    def reset(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM progress")


def append_parquet_dedup(
    out_path: Path,
    new_df: pd.DataFrame,
    subset_cols: List[str],
) -> None:
    """
    Append data to parquet file without duplicates.

    Parameters
    ----------
    out_path : Path
        Output parquet file.
    new_df : pd.DataFrame
        Data to append.
    subset_cols : List[str]
        Columns defining uniqueness.
    """

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if out_path.exists():
        old_df = pd.read_parquet(out_path)
        combined = pd.concat([old_df, new_df], ignore_index=True)
        combined = combined.drop_duplicates(subset=subset_cols, keep="last")
    else:
        combined = new_df.drop_duplicates(subset=subset_cols, keep="last")

    tmp = out_path.with_suffix(".tmp.parquet")
    combined.to_parquet(tmp, index=False)
    tmp.replace(out_path)


def chunked(iterable: Iterable, size: int) -> Iterable[List]:
    """
    Yield successive chunks from iterable.

    Parameters
    ----------
    iterable : Iterable
    size : int
        Chunk size.
    """
    iterable = list(iterable)
    for i in range(0, len(iterable), size):
        yield iterable[i:i + size]


def _verify_no_duplicates(path: Path) -> None:
    """
    Verify exported parquet files contain no duplicates.
    """

    for name, key in [
        ("events.parquet", "event_id"),
        ("picks.parquet", "pick_id"),
    ]:
        file = path / name
        if not file.exists():
            continue

        df = pd.read_parquet(file)
        if key in df.columns:
            dup = df.duplicated(subset=[key]).sum()
            if dup > 0:
                raise ValueError(
                    f"Duplicate {key} detected in {name}: {dup}"
                )
            

def to_parquet(
    bank,
    path: Path,
    stations: bool = False,
    events: bool = True,
    picks: bool = True,
    apply_utd_qc: bool = True,
    chunk_size: int = 100,
    overwrite: bool = True,
    qc_debug: bool = False
) -> None:
    """
    Export an ObsPlus EventBank to Parquet incrementally, saving by network.

    Parameters
    ----------
    bank : obsplus.EventBank
        Event bank instance.
    path : Path
        Output directory.
    stations : bool
        Export stations (placeholder).
    events : bool
        Export events.
    picks : bool
        Export picks.
    apply_utd_qc : bool
        Apply UTD QC before exporting.
    chunk_size : int
        Number of events per chunk.
    overwrite : bool
        Reset progress and rebuild.
    qc_debug : bool
        If True, print debug info during UTD QC.
    """

    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)

    # Extract network name from bank_path
    network_name = bank.bank_path.name  # last folder, e.g., 'RSNC'

    # Create subfolders
    events_folder = path / "events"
    picks_folder = path / "picks"
    progress_folder = path / ".progress"

    events_folder.mkdir(parents=True, exist_ok=True)
    picks_folder.mkdir(parents=True, exist_ok=True)
    progress_folder.mkdir(parents=True, exist_ok=True)

    # Define parquet file paths
    events_file = events_folder / f"network={network_name}.parquet"
    picks_file = picks_folder / f"network={network_name}.parquet"

    progress_file = progress_folder / f"network={network_name}.sqlite"
    progress = ParquetExportProgress(progress_file)

    if overwrite:
        logger.warning("Overwrite=True -> removing existing network data and progress.")

        # Remove parquet files for this network
        if events_file.exists():
            events_file.unlink()

        if picks_file.exists():
            picks_file.unlink()

        # Remove progress DB
        if progress_file.exists():
            progress_file.unlink()

        # Recreate fresh progress DB
        progress = ParquetExportProgress(progress_file)

    indices = bank.read_index()
    event_ids = indices["event_id"].unique()

    logger.info("Found %d events.", len(event_ids))

    for chunk in chunked(event_ids, chunk_size):
        logger.info("Processing chunk of %d events.", len(chunk))

        # Skip already processed
        chunk = [eid for eid in chunk if not progress.is_done(eid)]
        if not chunk:
            logger.info("Chunk already processed. Skipping.")
            continue

        cat = bank.get_events(event_id=chunk)

        if apply_utd_qc:
            logger.info("Applying UTD QC.")
            cat.apply_utdq_qc(debug=qc_debug, inplace=True)

        # ---------------- EVENTS ----------------
        if events:
            events_df = cat.utdq_events_to_df()
            events_df = sanitize_dataframe_for_parquet(events_df, **PREF_EVENTS_TYPES)
            existing_pref = [c for c in PREF_EVENTS_ORDER if c in events_df.columns]
            remaining = [c for c in events_df.columns if c not in existing_pref]
            events_df = events_df[existing_pref + remaining]

            append_parquet_dedup(
                events_file,
                events_df,
                subset_cols=["event_id"],
            )

        # ---------------- PICKS ----------------
        if picks:
            picks_df = cat.utdq_picks_to_df()
            picks_df = sanitize_dataframe_for_parquet(picks_df, **PREF_PICKS_TYPES)
            existing_pref = [c for c in PREF_PICKS_ORDER if c in picks_df.columns]
            remaining = [c for c in picks_df.columns if c not in existing_pref]
            picks_df = picks_df[existing_pref + remaining]

            subset = ["pick_id"] if "pick_id" in picks_df.columns else ["resource_id"]
            append_parquet_dedup(
                picks_file,
                picks_df,
                subset_cols=subset,
            )

        # Mark progress AFTER successful write
        for eid in chunk:
            progress.mark_done(eid)

    logger.info("Export complete. Running duplicate verification.")
    _verify_no_duplicates(path)
    logger.info("Export verified successfully.")
