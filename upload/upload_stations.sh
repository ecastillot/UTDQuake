#!/bin/bash
#SBATCH -N 1
#SBATCH -n 64
#SBATCH -p normal
#SBATCH -J UTDQZIPUP
#SBATCH -o /groups/igonin/ecastillo/utdquake/upload/upload_man_%j.out

set -euo pipefail

source /groups/igonin/ecastillo/anaconda3/etc/profile.d/conda.sh
conda activate utdq

BASE="/groups/igonin/ecastillo/UTDQuake"

STAGE="${BASE}/_hf_stage"

HF_WORKERS=4
echo "HF_WORKERS=$HF_WORKERS"

hf upload-large-folder ecastillot/UTDQuake "$STAGE" \
  --include "stations/*" \
  --repo-type dataset \
  --num-workers "$HF_WORKERS"

echo "✅ DONE"

#  hf upload-large-folder ecastillot/UTDQuake /groups/igonin/ecastillo/UTDQuake/manifests --include "network/*" --repo-type dataset --num-workers 4