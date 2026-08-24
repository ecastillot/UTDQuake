"""
Demo: how to upload a single file to the UTDQuake Hugging Face dataset repo.

Two ways, from low-level to high-level:

  1) huggingface_hub.HfApi.upload_file  -- uploads ANY single file to ANY
     path in the repo. Use this for one-off files (like this demo).
  2) utdquake.publish_network           -- the utdquake-specific helper
     (utdquake/hub.py) that uploads a whole network's manifests
     (events/stations/picks + merges network.parquet) in one commit.
     Only relevant once you have a real network's manifest layout on disk.

This script does NOT run on import -- call one of the functions below
explicitly, e.g.:

    python upload_example.py --target test-repo
    python upload_example.py --target real-repo   # pushes to ecastillot/UTDQuake

By default it targets a throwaway private test repo, not the real
production dataset, so you can see it work without touching real data.
"""
import argparse
import os

from huggingface_hub import HfApi

from utdquake.core.config import HF_REPO_ID, HF_REPO_TYPE

HERE = os.path.dirname(os.path.abspath(__file__))
LOCAL_FILE = os.path.join(HERE, "sample_data.txt")

# Where this test file goes to inside the repo -- any relative path works.
PATH_IN_REPO = "test/08192026/sample_data.txt"

TEST_REPO_ID = "ecastillot/utdquake-hub-livetest-demo"


def upload_with_hfapi(repo_id: str) -> str:
    """
    Lowest-level way to upload one file. Inputs you must supply:

    - path_or_fileobj : local path (or bytes/file object) of what to upload
    - path_in_repo     : destination path *inside* the repo
    - repo_id           : "<namespace>/<repo-name>" on the Hub
    - repo_type         : "dataset" for UTDQuake (vs "model"/"space")
    - token             : your HF token. HfApi() with no token reads it
                           from the HF_TOKEN env var, or from a cached
                           `huggingface-cli login`, automatically.
    - commit_message    : optional but recommended
    """
    token = os.environ.get("HF_TOKEN")  # or: huggingface-cli login once, and omit this
    api = HfApi(token=token)

    # create_repo is a no-op (exist_ok=True) if the repo already exists.
    api.create_repo(repo_id, repo_type=HF_REPO_TYPE, private=True, exist_ok=True)

    commit_info = api.upload_file(
        path_or_fileobj=LOCAL_FILE,
        path_in_repo=PATH_IN_REPO,
        repo_id=repo_id,
        repo_type=HF_REPO_TYPE,
        commit_message="Add hub upload demo file",
    )
    return commit_info.commit_url


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--target",
        choices=["test-repo", "real-repo"],
        default="test-repo",
        help="test-repo (default, safe) or real-repo (pushes to the real "
             f"{HF_REPO_ID} dataset used by everyone -- only use on purpose).",
    )
    args = parser.parse_args()

    repo_id = TEST_REPO_ID if args.target == "test-repo" else HF_REPO_ID
    print(f"Uploading {LOCAL_FILE} -> {repo_id}:{PATH_IN_REPO}")
    url = upload_with_hfapi(repo_id)
    print("Done:", url)
