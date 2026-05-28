#!/bin/bash
#SBATCH -N 1                
#SBATCH -n 20              
#SBATCH -p normal            
#SBATCH -J parquet
#SBATCH -o /groups/igonin/ecastillo/utdquake/scripts2/parquet/%x_%j.out

source /groups/igonin/ecastillo/anaconda3/etc/profile.d/conda.sh
conda activate utdq

python /groups/igonin/ecastillo/utdquake/scripts2/parquet/make_parquet.py

echo "✅ DONE"