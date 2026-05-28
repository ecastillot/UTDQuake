#!/bin/bash
#SBATCH -N 1                
#SBATCH -n 20              
#SBATCH -p normal            
#SBATCH -J utdq_figs      
#SBATCH -o /groups/igonin/ecastillo/utdquake/paper/utdq_travel_time.out

source /groups/igonin/ecastillo/anaconda3/etc/profile.d/conda.sh
conda activate utdq

python /groups/igonin/ecastillo/utdquake/paper/utdq_travel_time.py

echo "✅ DONE"