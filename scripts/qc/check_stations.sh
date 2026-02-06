#!/bin/bash
#SBATCH -N 1                
#SBATCH -n 64              
#SBATCH -p normal            
#SBATCH -J check_sta     
#SBATCH -o /groups/igonin/ecastillo/utdquake/scripts/qc/check_stations_%x_%j.out

source /groups/igonin/ecastillo/anaconda3/etc/profile.d/conda.sh
conda activate utdq

python /groups/igonin/ecastillo/utdquake/scripts/qc/check_stations.py

echo "✅ DONE"