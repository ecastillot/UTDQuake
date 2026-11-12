#!/bin/bash
#SBATCH -N 1
#SBATCH -n 4
#SBATCH --mem=32G
#SBATCH -p normal
#SBATCH -J test_merge
#SBATCH --time=02:00:00
#SBATCH -o /groups/igonin/ecastillo/UTDQuake/.utdquake/extend/v2.0/logs/%x_%j.out
source /groups/igonin/ecastillo/anaconda3/etc/profile.d/conda.sh
conda activate utdq
export PYTHONPATH=/groups/igonin/ecastillo/utdquake_v2ext UTDQUAKE_ROOT=/groups/igonin/ecastillo/UTDQuake HF_HUB_OFFLINE=1
python -W ignore /groups/igonin/ecastillo/utdquake_v2ext/datasets/extend/tests/test_merge.py /groups/igonin/ecastillo/UTDQuake/.utdquake/extend/v2.0/merge_test
