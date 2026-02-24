from __future__ import annotations

import os
import logging
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional, Dict, List
import pandas as pd


logger = logging.getLogger(__name__)

@dataclass(frozen=True)
class ManifestPaths:
    """
    Centralized manifest paths for UTDQuake, with selectable file format.

    Layout:

    root/
      manifests/
        events.{ext}
        stations.{ext}
        picks.{ext}
        network.{ext}
        progress.sqlite
    """

    root: Path
    manifest_dirname: str = "manifests"
    file_format: str = "parquet"  # 'parquet' or 'csv'

    progress_name: str = "progress.sqlite"

    @property
    def ext(self) -> str:
        if self.file_format.lower() not in ("parquet", "csv"):
            raise ValueError(f"Unsupported file format: {self.file_format}")
        return self.file_format.lower()

    @property
    def manifest_dir(self) -> Path:
        return self.root / self.manifest_dirname

    @property
    def network(self) -> Path:
        return self.manifest_dir / f"network.{self.ext}"

    @property
    def progress_db(self) -> Path:
        return self.manifest_dir / self.progress_name

    def ensure_dirs(self) -> None:
        self.manifest_dir.mkdir(parents=True, exist_ok=True)
        
    def get_events(self,network) -> Path:
        return self.manifest_dir / "events" / f"network={network}.{self.ext}"

    def get_stations(self,network) -> Path:
        return self.manifest_dir / "stations" / f"network={network}.{self.ext}"

    def get_picks(self,network) -> Path:
        return self.manifest_dir / "picks" / f"network={network}.{self.ext}"


# ---------------------------------------------------------------------
# Progress tracker (resume-safe)
# ---------------------------------------------------------------------
class ManifestProgress:
    """
    Tracks which networks were already processed for each manifest type.

    This avoids duplicates and supports resume after interruption.
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
                    manifest TEXT NOT NULL,
                    network TEXT NOT NULL,
                    status TEXT NOT NULL,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (manifest, network)
                )
                """
            )

    def is_done(self, manifest: str, network: str) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                "SELECT status FROM progress WHERE manifest=? AND network=?",
                (manifest, network),
            )
            row = cur.fetchone()
        return row is not None and row[0] == "done"

    def mark_done(self, manifest: str, network: str) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO progress (manifest, network, status)
                VALUES (?, ?, 'done')
                ON CONFLICT(manifest, network)
                DO UPDATE SET status='done', updated_at=CURRENT_TIMESTAMP
                """,
                (manifest, network),
            )

    def reset(self, manifest: Optional[str] = None) -> None:
        with sqlite3.connect(self.db_path) as conn:
            if manifest is None:
                conn.execute("DELETE FROM progress")
            else:
                conn.execute("DELETE FROM progress WHERE manifest=?", (manifest,))
