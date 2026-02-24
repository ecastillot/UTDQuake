#!/bin/bash
#SBATCH -N 1                
#SBATCH -n 64              
#SBATCH -p normal            
#SBATCH -J make_parquet   
#SBATCH -o /groups/igonin/ecastillo/utdquake/scripts/export/%x_%j.out

source /groups/igonin/ecastillo/anaconda3/etc/profile.d/conda.sh
conda activate utdq

python /groups/igonin/ecastillo/utdquake/scripts/export/make_parquet.py

echo "✅ DONE"