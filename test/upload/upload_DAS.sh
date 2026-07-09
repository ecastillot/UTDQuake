#!/bin/bash
#SBATCH -N 1
#SBATCH -n 1
#SBATCH -p normal
#SBATCH -J UTDQup
#SBATCH -o /groups/igonin/ecastillo/utdquake/upload/upload_DAS_%j.out

set -euo pipefail

source /groups/igonin/ecastillo/anaconda3/etc/profile.d/conda.sh
conda activate utdq

UTDQ="/groups/igonin/ecastillo/UTDQuake_DAS"

INCLUDE="events_DAS/**"

hf upload-large-folder ecastillot/UTDQuake "$UTDQ" --include "$INCLUDE" --repo-type dataset --num-workers 4

# hf upload-large-folder ecastillot/UTDQuake "/groups/igonin/ecastillo/UTDQuake_DAS" --include "banks_DAS/UWF.zip" --repo-type dataset --num-workers 4