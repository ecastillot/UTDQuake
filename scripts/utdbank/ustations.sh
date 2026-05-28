#!/bin/bash
#SBATCH -N 1                
#SBATCH -n 20              
#SBATCH -p normal            
#SBATCH -J ustations
#SBATCH -o /groups/igonin/ecastillo/utdquake/scripts/utdbank/%x_%j.out

source /groups/igonin/ecastillo/anaconda3/etc/profile.d/conda.sh
conda activate utdq

python /groups/igonin/ecastillo/utdquake/scripts/utdbank/ustations.py

echo "✅ DONE"