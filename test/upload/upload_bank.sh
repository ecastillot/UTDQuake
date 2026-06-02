#!/bin/bash
#SBATCH -N 1
#SBATCH -n 64
#SBATCH -p normal
#SBATCH -J UTDQup
#SBATCH -o /groups/igonin/ecastillo/utdquake/upload/upload_bank_%j.out

set -euo pipefail

source /groups/igonin/ecastillo/anaconda3/etc/profile.d/conda.sh
conda activate utdq

UTDQ="/groups/igonin/ecastillo/UTDQuake_DAS_upload"