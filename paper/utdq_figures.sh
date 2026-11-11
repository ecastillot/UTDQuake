#!/bin/bash
#SBATCH -N 1
#SBATCH -n 20
#SBATCH --mem=256G
#SBATCH -p normal
#SBATCH -J utdq_paper_figs
#SBATCH --time=12:00:00
#SBATCH -o /groups/igonin/ecastillo/utdquake/paper/utdq_figures_%j.out

# All paper figures (and figures/utdquake_overview.png) from UTDQuake 1.0 as published on the Hub
# (tag v1.0, see _local.py). Some figures only: sbatch utdq_figures.sh utdq_stats utdq_density
# Another checkout (e.g. a worktree): sbatch --export=ALL,UTDQ_REPO=<path> -o <log> utdq_figures.sh
source /groups/igonin/ecastillo/anaconda3/etc/profile.d/conda.sh
conda activate utdq
REPO=${UTDQ_REPO:-/groups/igonin/ecastillo/utdquake}
export PYTHONPATH=$REPO MPLBACKEND=Agg
cd $REPO/paper
# UTDQuake 1.0 as published (a local copy of the Hub tag, made once; see _local.py)
[ -d /groups/igonin/ecastillo/UTDQuake_paper_v1/events ] || python -W ignore _local.py
for f in ${@:-utdq_overview utdq_das utdq_stats utdq_density utdq_magnitude utdq_z_score utdq_travel_time}; do
    echo "$(date) $f"
    python -W ignore $f.py > $f.out 2>&1 && echo "  ok" || { echo "  FAILED"; tail -5 $f.out; }
done
echo "$(date) DONE"
