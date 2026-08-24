"""
Generate and publish the standard per-network figure set used in the
UTDQuake documentation (:ref:`overview-section`).

Two independent halves:

- ``generate_network_figures``: purely local, no credentials. Runs
  :class:`utdquake.Network`'s own ``plot_*`` methods and saves the results
  with the ``{network}_{suffix}.png`` naming already used on the ``figures``
  branch of https://github.com/ecastillot/UTDQuake.
- ``publish_network_figures``: uploads to GitHub. Needs a token
  (``GITHUB_TOKEN`` env var or ``token=``) with ``repo`` scope.
- ``overview_rst_row``: read-only, no token needed -- the repo is public.

Unlike the Hugging Face Hub, GitHub does not let a non-collaborator open a
PR without forking first. If the token does not have write access to
ecastillot/UTDQuake, ``publish_network_figures`` forks the repo under the
token's account, pushes the figures to that fork's ``figures`` branch, and
opens a PR back to ecastillot/UTDQuake. If the token does have write access
(a maintainer's), it commits directly instead.
"""

from __future__ import annotations

import base64
import logging
import time
from pathlib import Path
from typing import Dict, Optional

import requests

from .core.utdquake import Network

logger = logging.getLogger(__name__)

GITHUB_OWNER = "ecastillot"
GITHUB_REPO = "UTDQuake"
GITHUB_BRANCH = "figures"
GITHUB_TOKEN_ENV_VAR = "GITHUB_TOKEN"
GITHUB_API = "https://api.github.com"

# (suffix, Network method name, kwargs for that method, accepts a show= kwarg)
FIGURE_SPECS = [
    ("overview", "plot_overview", {}, True),
    ("stats", "plot_stats", {}, True),
    ("pick_histograms", "plot_pick_histograms", {}, True),
    ("phase_count_radar", "plot_phase_count_radar_by_magnitude", {}, True),
    ("station_location_uncertainty", "plot_station_location_uncertainty", {}, True),
    ("uncertainty_boxplots", "plot_uncertainty_boxplots", {}, True),
    ("travel_time_qc", "plot_travel_time_qc", {}, False),
    ("travel_time_vs_distance", "plot_travel_time_vs_distance", {}, True),
    ("travel_time_vs_distance_P_zscore", "plot_travel_time_vs_distance_zscore", {"phase": "P"}, True),
]


def generate_network_figures(
    network: str,
    outdir: Optional[Path] = None,
    das: bool = False,
) -> Dict[str, Path]:
    """
    Generate the standard figure set for a network.

    Each figure is generated independently -- one missing a prerequisite
    (e.g. no travel-time model yet) is logged and skipped rather than
    failing the whole batch.

    Parameters
    ----------
    network : str
        Network code, e.g. "CM".
    outdir : Path, optional
        Directory to save into. Defaults to ``./figures/{network}``.
    das : bool, optional
        Whether this is a DAS network. Default False.

    Returns
    -------
    dict[str, Path]
        ``{suffix: saved_path}`` for every figure that succeeded.
    """
    net = Network(network, das=das)
    outdir = Path(outdir) if outdir is not None else Path.cwd() / "figures" / network
    outdir.mkdir(parents=True, exist_ok=True)

    saved: Dict[str, Path] = {}
    for suffix, method_name, kwargs, accepts_show in FIGURE_SPECS:
        savepath = outdir / f"{network}_{suffix}.png"
        call_kwargs = dict(savepath=str(savepath), **kwargs)
        if accepts_show:
            call_kwargs["show"] = False
        try:
            getattr(net, method_name)(**call_kwargs)
            saved[suffix] = savepath
            logger.info("Generated %s", savepath)
        except Exception as e:
            logger.warning("Skipping %s for network %s: %s", suffix, network, e)
    return saved


def _resolve_token(token: Optional[str] = None) -> str:
    import os
    token = token or os.environ.get(GITHUB_TOKEN_ENV_VAR)
    if not token:
        raise ValueError(
            f"No GitHub token provided. Set the {GITHUB_TOKEN_ENV_VAR} "
            "environment variable or pass token=... explicitly."
        )
    return token


def _gh(method: str, url: str, token: str, **kwargs) -> requests.Response:
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    resp = requests.request(method, url, headers=headers, timeout=30, **kwargs)
    if resp.status_code >= 400:
        raise RuntimeError(f"GitHub API {method} {url} -> {resp.status_code}: {resp.text[:500]}")
    return resp


def _authenticated_user(token: str) -> str:
    return _gh("GET", f"{GITHUB_API}/user", token).json()["login"]


def _has_write_access(token: str, username: str) -> bool:
    resp = requests.get(
        f"{GITHUB_API}/repos/{GITHUB_OWNER}/{GITHUB_REPO}/collaborators/{username}/permission",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
        timeout=30,
    )
    if resp.status_code != 200:
        return False
    return resp.json().get("permission") in ("write", "admin")


def _ensure_fork(token: str, username: str) -> None:
    resp = requests.get(f"{GITHUB_API}/repos/{username}/{GITHUB_REPO}", headers={
        "Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"
    }, timeout=30)
    if resp.status_code == 200:
        return
    _gh("POST", f"{GITHUB_API}/repos/{GITHUB_OWNER}/{GITHUB_REPO}/forks", token)
    # Forking is async -- poll until the fork is queryable.
    for _ in range(20):
        time.sleep(1.5)
        resp = requests.get(f"{GITHUB_API}/repos/{username}/{GITHUB_REPO}", headers={
            "Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"
        }, timeout=30)
        if resp.status_code == 200:
            return
    raise RuntimeError(f"Timed out waiting for fork {username}/{GITHUB_REPO} to become available.")


def _put_file(owner: str, token: str, path_in_repo: str, local_path: Path, branch: str, message: str) -> None:
    url = f"{GITHUB_API}/repos/{owner}/{GITHUB_REPO}/contents/{path_in_repo}"
    existing = requests.get(url, params={"ref": branch}, headers={
        "Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"
    }, timeout=30)
    sha = existing.json().get("sha") if existing.status_code == 200 else None

    content_b64 = base64.b64encode(local_path.read_bytes()).decode("ascii")
    body = {"message": message, "content": content_b64, "branch": branch}
    if sha:
        body["sha"] = sha
    _gh("PUT", url, token, json=body)


def publish_network_figures(
    network: str,
    local_dir: Optional[Path] = None,
    token: Optional[str] = None,
    create_pr: bool = True,
    commit_message: Optional[str] = None,
) -> str:
    """
    Publish a network's already-generated figures (see
    :func:`generate_network_figures`) to the ``figures`` branch of
    ecastillot/UTDQuake on GitHub.

    Parameters
    ----------
    network : str
        Network code, e.g. "CM".
    local_dir : Path, optional
        Directory holding the generated PNGs. Defaults to
        ``./figures/{network}`` (matching ``generate_network_figures``'s
        default).
    token : str, optional
        GitHub personal access token (``repo`` scope). Defaults to the
        ``GITHUB_TOKEN`` environment variable.
    create_pr : bool, optional
        If True (default) and the token does *not* have write access to
        ecastillot/UTDQuake, fork the repo under the token's account, push
        the figures there, and open a PR back to ecastillot/UTDQuake -- no
        write access to the upstream repo required. If the token *does*
        have write access, this is ignored and the figures are committed
        directly to ecastillot/UTDQuake's ``figures`` branch regardless of
        this flag -- there's no reason to route a maintainer's own push
        through a fork.
    commit_message : str, optional
        Commit message. Defaults to a generated message.

    Returns
    -------
    str
        URL of the resulting commit (or PR, if ``create_pr=True``).
    """
    token = _resolve_token(token)
    local_dir = Path(local_dir) if local_dir is not None else Path.cwd() / "figures" / network
    pngs = sorted(local_dir.glob(f"{network}_*.png"))
    if not pngs:
        raise FileNotFoundError(f"No {network}_*.png files in {local_dir}. Run generate_network_figures first.")

    username = _authenticated_user(token)
    message = commit_message or f"Add figures for network {network}"

    if create_pr and not _has_write_access(token, username):
        _ensure_fork(token, username)
        target_owner = username
    else:
        target_owner = GITHUB_OWNER
        create_pr = False  # already a maintainer -- commit directly

    for png in pngs:
        _put_file(
            owner=target_owner,
            token=token,
            path_in_repo=f"figures/networks/{network}/{png.name}",
            local_path=png,
            branch=GITHUB_BRANCH,
            message=message,
        )
        logger.info("Uploaded %s to %s/%s@%s", png.name, target_owner, GITHUB_REPO, GITHUB_BRANCH)

    if not create_pr:
        return f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/tree/{GITHUB_BRANCH}/figures/networks/{network}"

    pr = _gh(
        "POST",
        f"{GITHUB_API}/repos/{GITHUB_OWNER}/{GITHUB_REPO}/pulls",
        token,
        json={
            "title": message,
            "head": f"{username}:{GITHUB_BRANCH}",
            "base": GITHUB_BRANCH,
            "body": f"Adds the figure set for network `{network}` (see :ref:`upload-dataset-section`).",
        },
    ).json()
    logger.info("Opened PR: %s", pr["html_url"])
    return pr["html_url"]


def overview_rst_row(network: str, das: bool = False) -> str:
    """
    Return the ``overview.rst`` list-table row for a network, ready to
    paste in: the real image row if figures exist on the ``figures``
    branch, or a "pending" placeholder row if not.

    This makes a single unauthenticated, read-only request -- no token
    needed, since the repo is public.
    """
    raw_url = (
        f"https://raw.githubusercontent.com/{GITHUB_OWNER}/{GITHUB_REPO}/"
        f"{GITHUB_BRANCH}/figures/networks/{network}/{network}_overview.png"
    )
    folder_url = f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/tree/{GITHUB_BRANCH}/figures/networks/{network}"

    exists = requests.head(raw_url, timeout=15).status_code == 200

    if exists:
        return (
            f"   * - {network}\n"
            f"     - `Open Folder <{folder_url}>`_\n"
            f"     - .. image:: {raw_url}\n"
            f"          :width: 200px\n"
        )
    return (
        f"   * - {network}\n"
        f"     - *pending*\n"
        f"     - *Figures pending -- see* :ref:`upload-dataset-section`\n"
    )
