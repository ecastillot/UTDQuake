#!/bin/bash
#SBATCH -N 1                
#SBATCH -n 20              
#SBATCH -p normal            
#SBATCH -J plot
#SBATCH -o /groups/igonin/ecastillo/utdquake/scripts2/das_fig/%x_%j.out

source /groups/igonin/ecastillo/anaconda3/etc/profile.d/conda.sh
conda activate utdq

python /groups/igonin/ecastillo/utdquake/scripts2/das_fig/utdq_network.py

echo "✅ DONE"