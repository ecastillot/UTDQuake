#!/bin/bash
#SBATCH -N 1
#SBATCH -n 64
#SBATCH -p normal
#SBATCH -J UTDQZIPUP
#SBATCH -o /groups/igonin/ecastillo/utdquake/upload/upload_pro_%j.out

set -euo pipefail

source /groups/igonin/ecastillo/anaconda3/etc/profile.d/conda.sh
conda activate utdq

BASE="/groups/igonin/ecastillo/UTDQuake"
STATIONS_SRC="${BASE}/stations"

STAGE="${BASE}/_hf_stage"


hf upload-large-folder ecastillot/UTDQuake "$STAGE" \
  --include "stations/*.zip" \
  --repo-type dataset \
  --num-workers "$HF_WORKERS"

echo "✅ DONE"
