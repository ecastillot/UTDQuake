#!/bin/bash
#SBATCH -N 1
#SBATCH -n 1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH -p normal
#SBATCH --time=1-00:00:00
# One step of tx_syn.py (R11), e.g.
#   mkdir -p logs
#   sbatch -J txsyn_sample -o logs/%x_%j.out run_tx_syn.sh sample
#   sbatch -J txsyn_tt --array=0-63 --cpus-per-task=1 --mem=8G -o logs/%x_%A_%a.out run_tx_syn.sh traveltimes --ntasks 64
#   sbatch -J txsyn_build -o logs/%x_%j.out run_tx_syn.sh build --root $PWD/UTDQuake_txsyn
#   sbatch -J txsyn_plots -o logs/%x_%j.out run_tx_syn.sh plots
set -u
source /groups/igonin/ecastillo/anaconda3/etc/profile.d/conda.sh
conda activate utdq
REPO=${UTDQ_REPO:-/groups/igonin/ecastillo/utdquake_v2ext}
export HF_HUB_OFFLINE=1 MPLBACKEND=Agg PYTHONPATH=$REPO
cd $REPO/datasets/tx_syn
echo "$(date) tx_syn $*"
python3 -W ignore tx_syn.py "$@"
rc=$?
echo "$(date) done rc=$rc"
exit $rc
