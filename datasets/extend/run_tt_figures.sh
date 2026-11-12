#!/bin/bash
#SBATCH -N 1
#SBATCH -n 4
#SBATCH --mem=96G
#SBATCH -p normal
#SBATCH --time=2-00:00:00
# Travel-time model + z-scores, stats and figures of merged networks (tt_figures.py). Each network has its own
# files, so several jobs can run at once on different networks.
#   L=$UTDQUAKE_ROOT/.utdquake/extend/v2.0/logs
#   sbatch -J ttfig_1 -o $L/%x_%j.out run_tt_figures.sh ETH JMA ci ...
REPO=${UTDQ_REPO:-/groups/igonin/ecastillo/utdquake}
source /groups/igonin/ecastillo/anaconda3/etc/profile.d/conda.sh
conda activate utdq
export UTDQUAKE_ROOT=${UTDQUAKE_ROOT:-/groups/igonin/ecastillo/UTDQuake} HF_HUB_OFFLINE=1 MPLBACKEND=Agg PYTHONPATH=$REPO
cd $REPO
echo "$(date) tt+figures: $*; code $REPO root $UTDQUAKE_ROOT"
python -W ignore $REPO/datasets/extend/tt_figures.py "$@"
rc=$?
echo "$(date) done rc=$rc"
exit $rc
