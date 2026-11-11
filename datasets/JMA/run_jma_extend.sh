#!/bin/bash
#SBATCH -N 1
#SBATCH -n 1
#SBATCH --cpus-per-task=2
#SBATCH --mem=24G
#SBATCH -p normal
#SBATCH -J jma_extend
#SBATCH --time=12:00:00
#SBATCH -o /groups/igonin/ecastillo/utdquake_v2ext/datasets/JMA/logs/%x_%j.out
# JMA events after the last v1 event, up to the v2.0 cap, into the extension bank (jma_to_utdq.py extend).
#   mkdir -p logs && sbatch run_jma_extend.sh [extend|replace-v1]
source /groups/igonin/ecastillo/anaconda3/etc/profile.d/conda.sh
conda activate utdq
export PYTHONPATH=/groups/igonin/ecastillo/utdquake_v2ext UTDQUAKE_ROOT=/groups/igonin/ecastillo/UTDQuake_v2 HF_HUB_OFFLINE=1
cd /groups/igonin/ecastillo/utdquake_v2ext/datasets/JMA
echo "$(date) start"
python -W ignore jma_to_utdq.py ${1:-extend}
echo "$(date) DONE (exit $?)"
