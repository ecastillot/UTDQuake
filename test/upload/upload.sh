#!/bin/bash
#SBATCH -N 1
#SBATCH -n 20
#SBATCH -p normal
#SBATCH -J UTDQup
#SBATCH -o /groups/igonin/ecastillo/utdquake/upload/upload_%j.out

set -euo pipefail

source /groups/igonin/ecastillo/anaconda3/etc/profile.d/conda.sh
conda activate utdq

UTDQ="/groups/igonin/ecastillo/UTDQuake"

INCLUDE="picks/**"

hf upload-large-folder ecastillot/UTDQuake "$UTDQ" --include "$INCLUDE" --repo-type dataset --num-workers 4