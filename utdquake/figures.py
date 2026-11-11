"""
Generate and publish the standard per-network figure set used in the
UTDQuake documentation (:ref:`overview-section`).

Two independent halves:

- ``generate_network_figures``: purely local, no credentials. Runs
  :class:`utdquake.Network`'s own ``plot_*`` methods and saves the results
  with the ``{utdq_net}_{suffix}.png`` naming used on the ``figures``
  branch of https://github.com/ecastillot/UTDQuake.
- ``publish_network_figures``: uploads to GitHub. Needs a token
  (``GITHUB_TOKEN`` env var or ``token=``) with ``repo`` scope. Also adds
  the network's row to ``docs/source/overview.rst`` on ``main`` by default
  (``update_overview=``) -- a different branch from the figures themselves,
  which go to ``figures``.
- ``overview_rst_row``: the network's card for the overview page; read-only, no token needed.

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
from .core.utils import renamed_kwarg

logger = logging.getLogger(__name__)

GITHUB_OWNER = "ecastillot"
GITHUB_REPO = "UTDQuake"
GITHUB_BRANCH = "figures"
GITHUB_DEFAULT_BRANCH = "main"  # where docs/source/overview.rst lives
GITHUB_TOKEN_ENV_VAR = "GITHUB_TOKEN"
GITHUB_API = "https://api.github.com"
OVERVIEW_RST_PATH = "docs/source/overview.rst"
# overview.rst is a gallery of network cards (raw HTML); new cards are inserted
# right before these markers, at the end of the Seismic Data / DAS Data galleries.
_SEISMIC_GALLERY_END = "   <!-- utdq-seismic-end -->"
_DAS_GALLERY_END = "   <!-- utdq-das-end -->"

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
    utdq_net: Optional[str] = None,
    outdir: Optional[Path] = None,
    das: bool = False,
    network: Optional[str] = None,
) -> Dict[str, Path]:
    """
    Generate the standard figure set for a network.

    Each figure is generated independently -- one missing a prerequisite
    (e.g. no travel-time model yet) is logged and skipped rather than
    failing the whole batch.

    Parameters
    ----------
    utdq_net : str
        UTDQuake network code, e.g. "CM".
    outdir : Path, optional
        Directory to save into. Defaults to ``./figures/{utdq_net}``.
    das : bool, optional
        Whether this is a DAS network. Default False.
    network : str, optional
        Deprecated alias of ``utdq_net``.

    Returns
    -------
    dict[str, Path]
        ``{suffix: saved_path}`` for every figure that succeeded.
    """
    network = renamed_kwarg(utdq_net, network, "utdq_net", "network", "generate_network_figures")
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


def _overview_card_markup(utdq_net: str, info: dict, folder_url: str, raw_url: str,
                          pending: bool = False) -> str:
    """
    One network card of the overview.rst gallery (raw HTML, indented for a
    ``.. raw:: html`` block): the utdq_net code, catalog, country and version,
    the overview figure (or a pending note) and the figures folder link.
    ``data-search`` holds the text the page's search box filters on.
    """
    from html import escape
    catalog = info.get("catalog") or ""
    version = info.get("dataset_version") or ""
    country = info.get("country") or ""
    continent = info.get("continent") or ""
    meta = " &middot; ".join(escape(x) for x in (catalog, country, version) if x)
    search = escape(" ".join([utdq_net, catalog, country, continent, version]).lower(), quote=True)
    if pending:
        body = '     <div class="utdq-pending">Figures pending</div>'
    else:
        body = (f'     <a href="{raw_url}" target="_blank"><img src="{raw_url}" loading="lazy" '
                f'alt="{escape(utdq_net)} overview"></a>')
    return (
        f'   <div class="utdq-card" data-net="{escape(utdq_net)}" data-search="{search}" '
        f'data-continent="{escape(continent)}" data-version="{escape(version)}">\n'
        f'     <div class="utdq-card-head"><span class="utdq-net">{escape(utdq_net)}</span>'
        f'<span class="utdq-meta">{meta}</span></div>\n'
        f"{body}\n"
        f'     <a class="utdq-folder" href="{folder_url}" target="_blank">Open folder &rarr;</a>\n'
        f"   </div>\n"
    )


def _network_info(utdq_net: str, das: bool = False) -> dict:
    """Card fields of a UTDQuake network from the published network table ('' if unknown)."""
    return {f: _network_field(utdq_net, f, das) for f in ("catalog", "dataset_version", "country", "continent")}


def _network_field(utdq_net: str, field: str, das: bool = False) -> str:
    """A field (``catalog``, ``dataset_version``) of a UTDQuake network from the published network table ('' if unknown)."""
    try:
        value = Network(utdq_net, das=das).description.get(field)
    except Exception as e:
        logger.warning("Could not read the %s of %s from the network table: %s", field, utdq_net, e)
        return ""
    return "" if value is None or str(value) in ("", "<NA>", "nan") else str(value)


def _catalog_of(utdq_net: str, das: bool = False) -> str:
    """The ``catalog`` of a UTDQuake network from the published network table ('' if unknown)."""
    return _network_field(utdq_net, "catalog", das)


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


def _update_overview_rst(owner: str, token: str, branch: str, network: str, message: str,
                         das: bool = False, catalog: Optional[str] = None) -> bool:
    """
    Insert the card of ``network`` into the Seismic Data or DAS Data gallery
    of ``overview.rst`` (per ``das``), committing directly to
    ``owner/UTDQuake@branch``. No-op (returns False) if the page already has
    a card for this network.
    """
    content, sha = _get_text_file(owner, token, OVERVIEW_RST_PATH, branch)

    if f'data-net="{network}"' in content:
        logger.info("overview.rst on %s@%s already has a card for %s -- leaving it as-is.", owner, branch, network)
        return False

    folder_url, raw_url = _network_urls(network, das)
    info = _network_info(network, das)
    if catalog is not None:
        info["catalog"] = catalog
    card = _overview_card_markup(network, info, folder_url, raw_url)

    marker = _DAS_GALLERY_END if das else _SEISMIC_GALLERY_END
    if marker not in content:
        raise RuntimeError(
            f"Could not find the {'DAS' if das else 'Seismic'} gallery end marker ({marker.strip()}) in "
            f"{OVERVIEW_RST_PATH} on {owner}@{branch} -- its layout may have changed. Add the card for "
            f"'{network}' manually (see overview_rst_row)."
        )
    new_content = content.replace(marker, card + marker, 1)

    _put_text_file(
        owner=owner, token=token, path_in_repo=OVERVIEW_RST_PATH,
        content=new_content, sha=sha, branch=branch, message=message,
    )
    return True


def publish_network_figures(
    utdq_net: Optional[str] = None,
    local_dir: Optional[Path] = None,
    token: Optional[str] = None,
    create_pr: bool = True,
    update_overview: bool = True,
    das: bool = False,
    commit_message: Optional[str] = None,
    catalog: Optional[str] = None,
    network: Optional[str] = None,
) -> str:
    """
    Publish a network's already-generated figures (see
    :func:`generate_network_figures`) to the ``figures`` branch of
    ecastillot/UTDQuake on GitHub, and add its row to ``overview.rst`` on
    the ``main`` branch.

    Parameters
    ----------
    utdq_net : str
        UTDQuake network code, e.g. "CM".
    local_dir : Path, optional
        Directory holding the generated PNGs. Defaults to
        ``./figures/{utdq_net}`` (matching ``generate_network_figures``'s
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
    catalog : str, optional
        Catalog shown in the new ``overview.rst`` row. Defaults to the
        network's ``catalog`` in the published network table.
    network : str, optional
        Deprecated alias of ``utdq_net``.

    Returns
    -------
    str
        URL of the resulting figures commit (or PR, if ``create_pr=True``).
        The ``overview.rst`` update's own commit/PR URL is only logged, not
        returned -- see the log output.
    """
    network = renamed_kwarg(utdq_net, network, "utdq_net", "network", "publish_network_figures")
    token = _resolve_token(token)
    local_dir = Path(local_dir) if local_dir is not None else Path.cwd() / "figures" / network
    pngs = sorted(local_dir.glob(f"{network}_*.png"))
    if not pngs:
        raise FileNotFoundError(f"No {network}_*.png files in {local_dir}. Run generate_network_figures first.")
    # text files next to the figures (e.g. {network}_catalog_description.txt: how a catalog was made) go too
    pngs += sorted(local_dir.glob(f"{network}_*.txt"))

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
                catalog=catalog,
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


def overview_rst_row(utdq_net: str, catalog: Optional[str] = None, das: bool = False) -> str:
    """
    Return the ``overview.rst`` gallery card (utdq_net, catalog, country,
    version, preview, figures folder) of a UTDQuake network, ready to paste
    before the gallery's end marker: with the preview if figures exist on the
    ``figures`` branch, else a "Figures pending" card.

    The card fields default to the network's row of the published network
    table. Checking the figures makes a single unauthenticated, read-only
    request -- no token needed, since the repo is public.
    """
    folder_url, raw_url = _network_urls(utdq_net, das)
    info = _network_info(utdq_net, das)
    if catalog is not None:
        info["catalog"] = catalog
    exists = requests.head(raw_url, timeout=15).status_code == 200
    return _overview_card_markup(utdq_net, info, folder_url, raw_url, pending=not exists)