#!/bin/bash
#SBATCH -N 1
#SBATCH -n 64
#SBATCH -p normal
#SBATCH -J UTDQbasic
#SBATCH -o /groups/igonin/ecastillo/utdquake/test/upload/upload_basic_%j.out

set -euo pipefail

source /groups/igonin/ecastillo/anaconda3/etc/profile.d/conda.sh
conda activate utdq

# Optional: disable hf_transfer for stability
export HF_HUB_ENABLE_HF_TRANSFER=0

UTDQ="/groups/igonin/ecastillo/UTDQuake"

# Optional: clear interrupted upload metadata
#rm -rf "$UTDQ/.cache/huggingface"

for f in "$UTDQ"/.utdquake/travel_time/*.parquet; do
    echo "Uploading $(basename "$f")"

    hf upload \
        ecastillot/UTDQuake \
        "$f" \
        ".utdquake/travel_time/$(basename "$f")" \
        --repo-type dataset

    echo "Finished $(basename "$f")"
done