#!/bin/bash
#SBATCH -N 1
#SBATCH -n 10
#SBATCH -p normal
#SBATCH -J UTDQZIPUP
#SBATCH -o /groups/igonin/ecastillo/utdquake/test/upload/upload_man_%j.out

set -euo pipefail

source /groups/igonin/ecastillo/anaconda3/etc/profile.d/conda.sh
conda activate utdq

UTDQ="/groups/igonin/ecastillo/UTDQuake"

INCLUDE=".utdquake/travel_time/*"

hf upload-large-folder ecastillot/UTDQuake "$UTDQ" --include "$INCLUDE" --repo-type dataset --num-workers 4