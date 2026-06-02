#!/bin/bash
#SBATCH -N 1
#SBATCH -n 64
#SBATCH -p normal
#SBATCH -J UTDQup
#SBATCH -o /groups/igonin/ecastillo/utdquake/test/upload/upload_zip_%j.out

set -euo pipefail

source /groups/igonin/ecastillo/anaconda3/etc/profile.d/conda.sh
conda activate utdq

BASE="/groups/igonin/ecastillo/UTDQuake"
HF_WORKERS=4

echo "Uploading to HuggingFace..."

hf upload-large-folder ecastillot/UTDQuake \
    "$BASE" \
    --include ".utdquake/*.zip" \
    --repo-type dataset \
    --num-workers "$HF_WORKERS"

echo "✅ DONE"