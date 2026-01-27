#!/bin/bash
#SBATCH -N 1                
#SBATCH -n 64              
#SBATCH -p normal            
#SBATCH -J save_picks      
#SBATCH -o /groups/igonin/ecastillo/utdquake/test/01192026/save_picks.out

source /groups/igonin/ecastillo/anaconda3/etc/profile.d/conda.sh
conda activate utdq

python /groups/igonin/ecastillo/utdquake/test/01192026/save_picks.py

echo "✅ DONE"
