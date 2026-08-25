"""
Generate and publish the standard per-network figure set used in the
UTDQuake documentation (:ref:`overview-section`).

Two independent halves:

- ``generate_network_figures``: purely local, no credentials. Runs
  :class:`utdquake.Network`'s own ``plot_*`` methods and saves the results
  with the ``{network}_{suffix}.png`` naming already used on the ``figures``
  branch of https://github.com/ecastillot/UTDQuake.
- ``publish_network_figures``: uploads to GitHub. Needs a token
  (``GITHUB_TOKEN`` env var or ``token=``) with ``repo`` scope. Also adds
  the network's row to ``docs/source/overview.rst`` on ``main`` by default
  (``update_overview=``) -- a different branch from the figures themselves,
  which go to ``figures``.
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
GITHUB_DEFAULT_BRANCH = "main"  # where docs/source/overview.rst lives
GITHUB_TOKEN_ENV_VAR = "GITHUB_TOKEN"
GITHUB_API = "https://api.github.com"
OVERVIEW_RST_PATH = "docs/source/overview.rst"
# Marks the end of the Seismic Data list-table in overview.rst -- new rows
# are inserted right before it.
_SEISMIC_TABLE_END_ANCHOR = "\n.. raw:: html\n\n\n   </div>\n\n.. _overview-DAS-data:"
# Marks the section header the DAS Data table lives under, and the closing
# block at the very end of the file -- new DAS rows are inserted right
# before that closing block.
_DAS_SECTION_MARKER = ".. _overview-DAS-data:"
_DAS_TABLE_END_ANCHOR = ".. raw:: html\n\n\n   </div>\n"

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


def _get_text_file(owner: str, token: str, path_in_repo: str, branch: str) -> tuple[str, str]:
    """Return (decoded text content, sha) of a file at owner/repo@branch."""
    url = f"{GITHUB_API}/repos/{owner}/{GITHUB_REPO}/contents/{path_in_repo}"
    data = _gh("GET", url, token, params={"ref": branch}).json()
    return base64.b64decode(data["content"]).decode("utf-8"), data["sha"]


def _put_text_file(owner: str, token: str, path_in_repo: str, content: str, sha: str, branch: str, message: str) -> None:
    url = f"{GITHUB_API}/repos/{owner}/{GITHUB_REPO}/contents/{path_in_repo}"
    body = {
        "message": message,
        "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
        "branch": branch,
        "sha": sha,
    }
    _gh("PUT", url, token, json=body)


def _overview_row_markup(network: str, folder_url: str, raw_url: str) -> str:
    return (
        f"   * - {network}\n"
        f"     - `Open Folder <{folder_url}>`_\n"
        f"     - .. image:: {raw_url}\n"
        f"          :width: 200px\n"
    )


def _network_remote_subdir(das: bool) -> str:
    return "networks_DAS" if das else "networks"


def _network_urls(network: str, das: bool = False) -> tuple[str, str]:
    """Return (folder_url, raw_url) for a network's figures on the ``figures`` branch."""
    subdir = _network_remote_subdir(das)
    folder_url = f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/tree/{GITHUB_BRANCH}/figures/{subdir}/{network}"
    raw_url = (
        f"https://raw.githubusercontent.com/{GITHUB_OWNER}/{GITHUB_REPO}/"
        f"{GITHUB_BRANCH}/figures/{subdir}/{network}/{network}_overview.png"
    )
    return folder_url, raw_url


def _update_overview_rst(owner: str, token: str, branch: str, network: str, message: str, das: bool = False) -> bool:
    """
    Insert the ``overview.rst`` row for ``network`` into the Seismic Data or
    DAS Data table (per ``das``), committing directly to
    ``owner/UTDQuake@branch``. No-op (returns False) if a row for this
    network is already there.
    """
    content, sha = _get_text_file(owner, token, OVERVIEW_RST_PATH, branch)

    if f"   * - {network}\n" in content:
        logger.info("overview.rst on %s@%s already has a row for %s -- leaving it as-is.", owner, branch, network)
        return False

    folder_url, raw_url = _network_urls(network, das)
    row = _overview_row_markup(network, folder_url, raw_url)

    if not das:
        if _SEISMIC_TABLE_END_ANCHOR not in content:
            raise RuntimeError(
                f"Could not find the Seismic Data table's end marker in {OVERVIEW_RST_PATH} on "
                f"{owner}@{branch} -- its layout may have changed. Add the row for "
                f"'{network}' manually (see overview_rst_row)."
            )
        replacement = "\n" + row + "\n" + _SEISMIC_TABLE_END_ANCHOR[1:]
        new_content = content.replace(_SEISMIC_TABLE_END_ANCHOR, replacement, 1)
    else:
        das_section_start = content.find(_DAS_SECTION_MARKER)
        anchor_idx = content.rfind(_DAS_TABLE_END_ANCHOR)
        if das_section_start == -1 or anchor_idx == -1 or anchor_idx < das_section_start:
            raise RuntimeError(
                f"Could not find the DAS Data table's end marker in {OVERVIEW_RST_PATH} on "
                f"{owner}@{branch} -- its layout may have changed. Add the row for "
                f"'{network}' manually (see overview_rst_row)."
            )
        prefix = content[:anchor_idx].rstrip("\n")
        suffix = content[anchor_idx:]
        new_content = prefix + "\n\n" + row + "\n\n" + suffix

    _put_text_file(
        owner=owner, token=token, path_in_repo=OVERVIEW_RST_PATH,
        content=new_content, sha=sha, branch=branch, message=message,
    )
    return True


def publish_network_figures(
    network: str,
    local_dir: Optional[Path] = None,
    token: Optional[str] = None,
    create_pr: bool = True,
    update_overview: bool = True,
    das: bool = False,
    commit_message: Optional[str] = None,
) -> str:
    """
    Publish a network's already-generated figures (see
    :func:`generate_network_figures`) to the ``figures`` branch of
    ecastillot/UTDQuake on GitHub, and add its row to ``overview.rst`` on
    the ``main`` branch.

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
    das : bool, optional
        Whether this is a DAS network. Default False. Controls both where
        the figures are uploaded (``figures/networks_DAS/{network}/`` vs.
        ``figures/networks/{network}/``) and, when ``update_overview`` is
        True, which ``overview.rst`` table (DAS Data vs. Seismic Data) gets
        the new row.
    create_pr : bool, optional
        If True (default) and the token does *not* have write access to
        ecastillot/UTDQuake, fork the repo under the token's account, push
        the figures there, and open a PR back to ecastillot/UTDQuake -- no
        write access to the upstream repo required. If the token *does*
        have write access, this is ignored and the figures are committed
        directly to ecastillot/UTDQuake's ``figures`` branch regardless of
        this flag -- there's no reason to route a maintainer's own push
        through a fork.
    update_overview : bool, optional
        If True (default), also add ``network``'s row to
        ``docs/source/overview.rst``. This always targets the ``main``
        branch -- a *different* branch from the figures themselves, which
        go to ``figures`` -- since that's where the docs live. Maintainers
        get this committed directly to ecastillot/UTDQuake's ``main``
        (requires write access to ``main`` specifically; if ``main`` is
        branch-protected this step will fail even though the figures
        upload already succeeded -- pass ``update_overview=False`` and
        edit ``overview.rst`` by hand in that case). Non-maintainers get a
        *second*, separate pull request opened against ``main`` (a PR can
        only target one base branch, so it can't be folded into the
        figures PR against ``figures``). A no-op if the network already
        has a row.
    commit_message : str, optional
        Commit message. Defaults to a generated message.

    Returns
    -------
    str
        URL of the resulting figures commit (or PR, if ``create_pr=True``).
        The ``overview.rst`` update's own commit/PR URL is only logged, not
        returned -- see the log output.
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

    remote_subdir = _network_remote_subdir(das)

    for png in pngs:
        _put_file(
            owner=target_owner,
            token=token,
            path_in_repo=f"figures/{remote_subdir}/{network}/{png.name}",
            local_path=png,
            branch=GITHUB_BRANCH,
            message=message,
        )
        logger.info("Uploaded %s to %s/%s@%s", png.name, target_owner, GITHUB_REPO, GITHUB_BRANCH)

    if update_overview:
        overview_message = f"Add {network} to overview.rst"
        try:
            changed = _update_overview_rst(
                owner=target_owner,
                token=token,
                branch=GITHUB_DEFAULT_BRANCH,
                network=network,
                message=overview_message,
                das=das,
            )
            if changed and create_pr:
                overview_pr = _gh(
                    "POST",
                    f"{GITHUB_API}/repos/{GITHUB_OWNER}/{GITHUB_REPO}/pulls",
                    token,
                    json={
                        "title": overview_message,
                        "head": f"{username}:{GITHUB_DEFAULT_BRANCH}",
                        "base": GITHUB_DEFAULT_BRANCH,
                        "body": (
                            f"Adds the `overview.rst` row for network `{network}`. "
                            f"Depends on the figures PR for `{network}` being merged first, "
                            "otherwise the preview image will 404."
                        ),
                    },
                ).json()
                logger.info("Opened overview.rst PR: %s", overview_pr["html_url"])
            elif changed:
                logger.info(
                    "Committed overview.rst update to %s/%s@%s",
                    GITHUB_OWNER, GITHUB_REPO, GITHUB_DEFAULT_BRANCH,
                )
        except Exception as e:
            logger.warning(
                "Figures for %s published, but updating overview.rst failed: %s. "
                "Add its row manually (see overview_rst_row).", network, e,
            )

    if not create_pr:
        return f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/tree/{GITHUB_BRANCH}/figures/{remote_subdir}/{network}"

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
    folder_url, raw_url = _network_urls(network, das)

    exists = requests.head(raw_url, timeout=15).status_code == 200

    if exists:
        return _overview_row_markup(network, folder_url, raw_url)
    return (
        f"   * - {network}\n"
        f"     - *pending*\n"
        f"     - *Figures pending -- see* :ref:`upload-dataset-section`\n"
    )
