from __future__ import annotations

from dataclasses import dataclass

DEFAULT_REPO_ID = "ecastillot/UTDQuake"
DEFAULT_REPO_TYPE = "dataset"
ENV_CACHE_ROOT = "UTDQUAKE_ROOT"


@dataclass(frozen=True)
class UTDQuakeConfig:
    repo_id: str = DEFAULT_REPO_ID
    repo_type: str = DEFAULT_REPO_TYPE
    env_cache_root: str = ENV_CACHE_ROOT
