#!/bin/bash
#SBATCH -N 1
#SBATCH -n 1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH -p normal
#SBATCH -J antarctica_build
#SBATCH --time=12:00:00
#SBATCH -o /groups/igonin/ecastillo/utdquake/datasets/R12-Antartic/logs/%x_%j.out

# Builds the candidate network R12 (East Antarctica) or R13 (West Antarctica), Ho et al., locally: catalogs -> QC -> bank -> stations -> picks
# -> manifests -> travel-time model (+ z-scores) -> pick_agency -> stats and figures (figures/networks/R12).
# Does not publish and does not touch the main dataset. The build runs in the node's local /tmp (the sqlite
# station databases are much faster there); the finished root is copied to $ROOT (also on failure).
#
#   mkdir -p logs && sbatch run_build.sh R12      (or R13)

set -u
NET=${1:?usage: sbatch run_build.sh R12|R13}
source /groups/igonin/ecastillo/anaconda3/etc/profile.d/conda.sh
conda activate utdq
export HF_HUB_OFFLINE=1 MPLBACKEND=Agg PYTHONPATH=/groups/igonin/ecastillo/utdquake
cd /groups/igonin/ecastillo/utdquake/datasets/R12-Antartic

ROOT=/groups/igonin/ecastillo/utdquake/datasets/R12-Antartic/UTDQuake_$NET
LOCAL=/tmp/${USER}_${NET}_${SLURM_JOB_ID}
[ -e "$ROOT" ] && { echo "$ROOT exists: move it away first"; exit 1; }
mkdir -p "$LOCAL"
trap 'echo "$(date) copying $LOCAL -> $ROOT"; mkdir -p "$ROOT"; rsync -a "$LOCAL"/ "$ROOT"/ && rm -rf "$LOCAL"' EXIT

echo "$(date) build"
python3 -W ignore antarctica_to_utdq.py --net $NET --root "$LOCAL" || exit 1
echo "$(date) DONE"
