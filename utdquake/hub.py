"""
Publish and remove per-network datasets on the shared UTDQuake Hugging
Face Hub dataset repository (:data:`utdquake.core.config.HF_REPO_ID`).

Unlike ``core.data`` (download-only), this module writes to the shared
repo, so every function requires an explicit Hugging Face token (from the
``HF_TOKEN`` environment variable or the ``token`` argument) and performs
a single atomic commit per call.

``events``, ``stations`` and ``picks`` are stored as one file per network,
so publishing/removing a network only ever touches that network's own
files. ``network.parquet`` is a single file shared by every network, so
it is merged (update-or-append the row for this network, keyed by
``network``) rather than overwritten, and the commit is anchored to the
revision it was read from (``parent_commit``) so a concurrent publish by
someone else is detected as a conflict instead of silently lost.
``publish_network`` stamps the merged row's ``last_published`` column with
the actual upload time (UTC), overriding whatever was in the local file.

Contributors who are not maintainers of the shared repo (no write access)
should pass ``create_pr=True``: this opens a Pull Request with their own
token instead of committing directly, and does not require any elevated
access -- the maintainer reviews and merges it from the Hub UI.
"""

from __future__ import annotations

import logging
import os
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Optional

import pandas as pd
from huggingface_hub import (
    CommitOperationAdd,
    CommitOperationDelete,
    HfApi,
    hf_hub_download,
)
from huggingface_hub.errors import HfHubHTTPError

from .core.config import HF_REPO_ID, HF_REPO_TYPE, get_hf_entry, get_root

logger = logging.getLogger(__name__)

HF_TOKEN_ENV_VAR = "HF_TOKEN"


def _resolve_token(token: Optional[str] = None) -> str:
    token = token or os.environ.get(HF_TOKEN_ENV_VAR)
    if not token:
        raise ValueError(
            f"No Hugging Face token provided. Set the {HF_TOKEN_ENV_VAR} "
            "environment variable or pass token=... explicitly."
        )
    return token


def _local_manifest_path(root: Path, key: str, network: str, das: bool) -> Path:
    return root / get_hf_entry(key, das).path.format(network=network)


def _download_networks_table(
    api: HfApi, token: str, das: bool
) -> tuple[pd.DataFrame, Optional[str]]:
    """
    Return (networks_df, revision) for the current network.parquet on the
    Hub, or (empty df, None) if the repo/file does not exist yet.
    """
    remote_path = get_hf_entry("networks", das).path
    try:
        info = api.dataset_info(HF_REPO_ID, token=token)
        revision = info.sha
        local_copy = hf_hub_download(
            repo_id=HF_REPO_ID,
            repo_type=HF_REPO_TYPE,
            filename=remote_path,
            revision=revision,
            token=token,
        )
        return pd.read_parquet(local_copy), revision
    except (HfHubHTTPError, FileNotFoundError, EnvironmentError):
        logger.info(
            "No existing %s on %s yet; starting from an empty networks table.",
            remote_path, HF_REPO_ID,
        )
        return pd.DataFrame(columns=["network"]), None


def publish_network(
    network: str,
    local_root: Optional[Path] = None,
    das: bool = False,
    include_banks: bool = True,
    include_travel_time: bool = False,
    token: Optional[str] = None,
    commit_message: Optional[str] = None,
    create_pr: bool = False,
) -> str:
    """
    Publish one network's manifests to the shared UTDQuake Hub repo.

    Expects ``local_root`` to already contain the flat manifest layout
    produced by ``utdquake.writers.parquet.build_manifests`` (e.g.
    ``root/events/network={network}.parquet``, ``root/stations/...``,
    ``root/picks/...``, and a row for this network in
    ``root/network/network.parquet``) -- run that first.

    Parameters
    ----------
    network : str
        Network code to publish, e.g. "CM".
    local_root : Path, optional
        Directory holding the local manifest layout. Defaults to
        ``get_root(das=das)``.
    das : bool, optional
        Whether this is a DAS dataset. Default False.
    include_banks : bool, optional
        If True, also zip and upload the local EventBank directory for
        this network. Default True -- Network.events/stations/picks
        (via resolve_network_paths) require the bank locally by default,
        so publishing without it leaves the network partially unusable.
        Requires the local bank directory to exist; pass False explicitly
        if you're re-publishing a network without the bank still on disk.
    include_travel_time : bool, optional
        If True, also upload the local travel-time model (see
        ``utdquake.qc.travel_time.build_travel_time_model``) so other
        users can load it too. Without this, ``Network.travel_time``,
        ``plot_travel_time_qc()``, and ``plot_travel_time_vs_distance_zscore()``
        only work locally, for whoever built the model. Default False.
    token : str, optional
        Hugging Face token. Defaults to the ``HF_TOKEN`` environment
        variable. A contributor without write access to the repo only
        needs *their own* token (read access is enough) when
        ``create_pr=True``.
    commit_message : str, optional
        Commit message. Defaults to a generated message.
    create_pr : bool, optional
        If True, opens a Pull Request with these changes instead of
        committing directly. Use this for anyone who is not a maintainer
        of the shared repo -- it does not require write access. Default
        False.

    Returns
    -------
    str
        URL of the resulting commit (or PR, if ``create_pr=True``) on the Hub.
    """
    token = _resolve_token(token)
    root = Path(local_root) if local_root is not None else get_root(das=das)
    api = HfApi(token=token)

    operations = []
    tmp_files: list[Path] = []

    try:
        # --- events / stations / picks: independent per-network shards ---
        for key in ("events", "stations", "picks"):
            local_path = _local_manifest_path(root, key, network, das)
            if not local_path.exists():
                logger.warning(
                    "No local %s manifest for network %s at %s; skipping.",
                    key, network, local_path,
                )
                continue
            remote_path = get_hf_entry(key, das).path.format(network=network)
            operations.append(
                CommitOperationAdd(path_in_repo=remote_path, path_or_fileobj=str(local_path))
            )

        # --- optional bank zip ---
        if include_banks:
            bank_dir = root / "banks" / network
            if not bank_dir.exists():
                raise FileNotFoundError(f"No local bank directory for network {network} at {bank_dir}")
            tmp_zip = Path(tempfile.mkstemp(suffix=".zip")[1])
            tmp_files.append(tmp_zip)
            with zipfile.ZipFile(tmp_zip, "w", zipfile.ZIP_DEFLATED) as zf:
                for file_path in bank_dir.rglob("*"):
                    if file_path.is_file():
                        # Store entries relative to bank_dir's PARENT (i.e.
                        # prefixed with "{network}/"), matching the existing
                        # zip format on HF (verified against banks/tx.zip)
                        # and what download_snapshot's extractall(zip_file.parent)
                        # expects - relative to bank_dir alone drops the
                        # network folder and the bank ends up at the wrong path.
                        zf.write(file_path, file_path.relative_to(bank_dir.parent))
            remote_path = get_hf_entry("banks", das).path.format(network=network)
            operations.append(
                CommitOperationAdd(path_in_repo=remote_path, path_or_fileobj=str(tmp_zip))
            )

        # --- optional travel-time model ---
        if include_travel_time:
            tt_path = root / get_hf_entry(".utdquake/travel_time", das).path.format(network=network)
            if not tt_path.exists():
                raise FileNotFoundError(
                    f"No local travel-time model for network {network} at {tt_path}. "
                    "Run utdquake.qc.travel_time.build_travel_time_model first."
                )
            remote_path = get_hf_entry(".utdquake/travel_time", das).path.format(network=network)
            operations.append(
                CommitOperationAdd(path_in_repo=remote_path, path_or_fileobj=str(tt_path))
            )

        # --- network.parquet: shared file, update-or-append this network's row ---
        local_networks_path = root / get_hf_entry("networks", das).path
        if not local_networks_path.exists():
            raise FileNotFoundError(
                f"No local network manifest at {local_networks_path}. "
                "Run build_manifests(include_networks=True) first."
            )
        local_row = pd.read_parquet(local_networks_path)
        local_row = local_row[local_row["network"] == network].copy()
        if local_row.empty:
            raise ValueError(f"Local network manifest has no row for network={network!r}.")
        # Stamp with the actual moment of upload -- not written back to the
        # local file, only to what gets published.
        local_row["last_published"] = pd.Timestamp.utcnow().tz_localize(None)

        remote_networks, parent_commit = _download_networks_table(api, token, das)
        merged = pd.concat([remote_networks, local_row], ignore_index=True)
        merged = merged.drop_duplicates(subset=["network"], keep="last")

        tmp_networks = Path(tempfile.mkstemp(suffix=".parquet")[1])
        tmp_files.append(tmp_networks)
        merged.to_parquet(tmp_networks, index=False)
        operations.append(
            CommitOperationAdd(
                path_in_repo=get_hf_entry("networks", das).path,
                path_or_fileobj=str(tmp_networks),
            )
        )

        if not operations:
            raise ValueError(f"Nothing to publish for network={network!r}: no local manifests found.")

        commit_info = api.create_commit(
            repo_id=HF_REPO_ID,
            repo_type=HF_REPO_TYPE,
            operations=operations,
            commit_message=commit_message or f"Publish network {network}",
            parent_commit=parent_commit,
            token=token,
            create_pr=create_pr,
        )
        result_url = commit_info.pr_url if create_pr else commit_info.commit_url
        logger.info(
            "Published network %s to %s%s: %s",
            network, HF_REPO_ID, " (as PR)" if create_pr else "", result_url,
        )
        return result_url
    finally:
        for f in tmp_files:
            f.unlink(missing_ok=True)


def remove_network(
    network: str,
    das: bool = False,
    include_banks: bool = False,
    include_travel_time: bool = False,
    token: Optional[str] = None,
    commit_message: Optional[str] = None,
    create_pr: bool = False,
) -> str:
    """
    Remove one network's files from the shared UTDQuake Hub repo and drop
    its row from ``network.parquet``.

    Parameters
    ----------
    network : str
        Network code to remove, e.g. "CM".
    das : bool, optional
        Whether this is a DAS dataset. Default False.
    include_banks : bool, optional
        If True, also delete the bank zip for this network. Default False.
    include_travel_time : bool, optional
        If True, also delete the travel-time model for this network.
        Default False.
    token : str, optional
        Hugging Face token. Defaults to the ``HF_TOKEN`` environment
        variable.
    commit_message : str, optional
        Commit message. Defaults to a generated message.
    create_pr : bool, optional
        If True, opens a Pull Request with this removal instead of
        committing directly. Default False.

    Returns
    -------
    str
        URL of the resulting commit (or PR, if ``create_pr=True``) on the Hub.
    """
    token = _resolve_token(token)
    api = HfApi(token=token)

    operations = []
    tmp_files: list[Path] = []

    try:
        keys = (
            ["events", "stations", "picks"]
            + (["banks"] if include_banks else [])
            + ([".utdquake/travel_time"] if include_travel_time else [])
        )
        for key in keys:
            remote_path = get_hf_entry(key, das).path.format(network=network)
            if api.file_exists(HF_REPO_ID, remote_path, repo_type=HF_REPO_TYPE, token=token):
                operations.append(CommitOperationDelete(path_in_repo=remote_path))
            else:
                logger.warning("Remote file %s does not exist; nothing to delete.", remote_path)

        remote_networks, parent_commit = _download_networks_table(api, token, das)
        if network in set(remote_networks.get("network", [])):
            remaining = remote_networks[remote_networks["network"] != network]
            tmp_networks = Path(tempfile.mkstemp(suffix=".parquet")[1])
            tmp_files.append(tmp_networks)
            remaining.to_parquet(tmp_networks, index=False)
            operations.append(
                CommitOperationAdd(
                    path_in_repo=get_hf_entry("networks", das).path,
                    path_or_fileobj=str(tmp_networks),
                )
            )

        if not operations:
            raise ValueError(f"Nothing to remove for network={network!r}: no matching remote files.")

        commit_info = api.create_commit(
            repo_id=HF_REPO_ID,
            repo_type=HF_REPO_TYPE,
            operations=operations,
            commit_message=commit_message or f"Remove network {network}",
            parent_commit=parent_commit,
            token=token,
            create_pr=create_pr,
        )
        result_url = commit_info.pr_url if create_pr else commit_info.commit_url
        logger.info(
            "Removed network %s from %s%s: %s",
            network, HF_REPO_ID, " (as PR)" if create_pr else "", result_url,
        )
        return result_url
    finally:
        for f in tmp_files:
            f.unlink(missing_ok=True)
