#!/bin/bash
#SBATCH -N 1                
#SBATCH -n 64              
#SBATCH -p normal            
#SBATCH -J utbank  
#SBATCH -o /groups/igonin/ecastillo/utdquake/scripts/utdbank/%x_%j.out

source /groups/igonin/ecastillo/anaconda3/etc/profile.d/conda.sh
conda activate utdq

python /groups/igonin/ecastillo/utdquake/scripts/utdbank/utbank.py

echo "✅ DONE"