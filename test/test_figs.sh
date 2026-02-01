#!/bin/bash
#SBATCH -N 1                
#SBATCH -n 64              
#SBATCH -p normal            
#SBATCH -J utdq_figs      
#SBATCH -o /groups/igonin/ecastillo/utdquake/test/%x_%j.out

source /groups/igonin/ecastillo/anaconda3/etc/profile.d/conda.sh
conda activate utdq

python /groups/igonin/ecastillo/utdquake/test/test_figs.py

echo "✅ DONE"