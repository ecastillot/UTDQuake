#!/bin/bash
#SBATCH -N 1
#SBATCH -n 4
#SBATCH --mem=64G
#SBATCH -p normal
#SBATCH --time=08:00:00
# v2.0 ISC IR step: decide the new IR stations (analyze, read-only), then apply all decisions to UTDQuake_v2
# (backup .utdquake/backups/v2.0_ir first; validation inside).
#   sbatch -J ir_v2 -o logs/%x_%j.out run_ir_v2.sh
source /groups/igonin/ecastillo/anaconda3/etc/profile.d/conda.sh
conda activate utdq
export PYTHONPATH=/groups/igonin/ecastillo/utdquake_v2ext HF_HUB_OFFLINE=1
cd /groups/igonin/ecastillo/utdquake_v2ext/datasets/isc_ir_v2
echo "$(date) analyze"; python -W ignore analyze_ir_stations.py || exit 1
echo "$(date) apply"; python -W ignore apply_ir_decisions.py; rc=$?
echo "$(date) done rc=$rc"; exit $rc
