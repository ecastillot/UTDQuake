#!/bin/bash
#SBATCH -N 1
#SBATCH -n 64
#SBATCH -p normal
#SBATCH -J UTDQup
#SBATCH -o /groups/igonin/ecastillo/utdquake/upload/upload_DAS_%j.out

set -euo pipefail

source /groups/igonin/ecastillo/anaconda3/etc/profile.d/conda.sh
conda activate utdq

UTDQ="/groups/igonin/ecastillo/UTDQuake"

INCLUDE="picks/**"

hf upload-large-folder ecastillot/UTDQuake "$UTDQ" --include "$INCLUDE" --repo-type dataset --num-workers 4