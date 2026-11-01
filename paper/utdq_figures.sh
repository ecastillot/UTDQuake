#!/bin/bash
#SBATCH -N 1
#SBATCH -n 20
#SBATCH --mem=256G
#SBATCH -p normal
#SBATCH -J utdq_paper_figs
#SBATCH --time=12:00:00
#SBATCH -o /groups/igonin/ecastillo/utdquake_schema/paper/utdq_figures_%j.out

# All paper figures (and figures/utdquake_overview.png) from the local UTDQuake 1.0 root, paper
# networks only (see _local.py).
source /groups/igonin/ecastillo/anaconda3/etc/profile.d/conda.sh
conda activate utdq
export PYTHONPATH=/groups/igonin/ecastillo/utdquake_schema MPLBACKEND=Agg
cd /groups/igonin/ecastillo/utdquake_schema/paper
for f in utdq_overview utdq_das utdq_stats utdq_density utdq_magnitude utdq_z_score utdq_travel_time; do
    echo "$(date) $f"
    python -W ignore $f.py > $f.out 2>&1 && echo "  ok" || { echo "  FAILED"; tail -5 $f.out; }
done
echo "$(date) DONE"
