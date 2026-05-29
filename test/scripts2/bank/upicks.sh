#!/bin/bash
#SBATCH -N 1                
#SBATCH -n 20              
#SBATCH -p normal            
#SBATCH -J put_picks
#SBATCH -o /groups/igonin/ecastillo/utdquake/scripts2/bank/%x_%j.out

source /groups/igonin/ecastillo/anaconda3/etc/profile.d/conda.sh
conda activate utdq

python /groups/igonin/ecastillo/utdquake/scripts2/bank/utdq_put_picks.py

echo "✅ DONE"