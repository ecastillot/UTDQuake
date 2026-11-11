#!/bin/bash
#SBATCH -N 1
#SBATCH -n 1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH -p normal
#SBATCH -J detect_build
#SBATCH --time=12:00:00
#SBATCH -o /groups/igonin/ecastillo/utdquake_v2ext/datasets/DETECT/logs/%x_%j.out

# Builds R10 (DETECT) locally: catalog -> QC -> bank -> stations -> picks -> manifests -> travel-time
# model (+ z-scores) -> pick_agency -> stats and figures (figures/networks/R10). Does not publish.
# The build runs in the node's local /tmp (the sqlite station
# databases are much faster there) and the finished root is copied to $ROOT (also on failure).
#
#   mkdir -p logs && sbatch run_detect_build.sh

set -u
source /groups/igonin/ecastillo/anaconda3/etc/profile.d/conda.sh
conda activate utdq
export HF_HUB_OFFLINE=1 MPLBACKEND=Agg PYTHONPATH=/groups/igonin/ecastillo/utdquake_v2ext
cd /groups/igonin/ecastillo/utdquake_v2ext/datasets/DETECT

ROOT=/groups/igonin/ecastillo/utdquake_v2ext/datasets/DETECT/UTDQuake_DETECT
LOCAL=/tmp/${USER}_detect_${SLURM_JOB_ID}
rm -rf "$ROOT"
mkdir -p "$LOCAL"
trap 'echo "$(date) copying $LOCAL -> $ROOT"; mkdir -p "$ROOT"; rsync -a "$LOCAL"/ "$ROOT"/ && rm -rf "$LOCAL"' EXIT

echo "$(date) build"
python3 -W ignore detect_to_utdq.py --root "$LOCAL" || exit 1
echo "$(date) DONE"
