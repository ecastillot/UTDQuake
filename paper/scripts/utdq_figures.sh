#!/bin/bash
#SBATCH -N 1
#SBATCH -n 20
#SBATCH --mem=256G
#SBATCH -p normal
#SBATCH -J utdq_paper_figs
#SBATCH --time=12:00:00

# All paper figures of a dataset version into paper/<version>/, logs in paper/<version>/logs/ (see _local.py):
# PAPER_VERSION=v1 (default: UTDQuake 1.0 as published on the Hub) or v2 (the working copy UTDQuake).
#   cd paper && sbatch --export=ALL,PAPER_VERSION=v2 -o v2/logs/utdq_figures_%j.out scripts/utdq_figures.sh
# Some figures only:  ... scripts/utdq_figures.sh utdq_stats utdq_density
# Another checkout (e.g. a worktree): add UTDQ_REPO=<path> to --export.
source /groups/igonin/ecastillo/anaconda3/etc/profile.d/conda.sh
conda activate utdq
REPO=${UTDQ_REPO:-/groups/igonin/ecastillo/utdquake}
export PYTHONPATH=$REPO MPLBACKEND=Agg
cd $REPO/paper/scripts
# UTDQuake 1.0 as published (a local copy of the Hub tag, made once; see _local.py)
[ "${PAPER_VERSION:-v1}" != v1 ] || [ -d /groups/igonin/ecastillo/UTDQuake_paper_v1/events ] || python -W ignore _local.py
LOGS=../${PAPER_VERSION:-v1}/logs; mkdir -p $LOGS
for f in ${@:-utdq_overview utdq_das utdq_stats utdq_density utdq_magnitude utdq_z_score utdq_travel_time}; do
    echo "$(date) $f"
    python -W ignore $f.py > $LOGS/$f.out 2>&1 && echo "  ok" || { echo "  FAILED"; tail -5 $LOGS/$f.out; }
done
echo "$(date) DONE"
