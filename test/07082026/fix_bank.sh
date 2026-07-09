#!/bin/bash
#SBATCH -N 1                
#SBATCH -n 1              
#SBATCH -p normal            
#SBATCH -J fixbank  
#SBATCH -o /groups/igonin/ecastillo/utdquake/test/07082026/%x_%j.out

source /groups/igonin/ecastillo/anaconda3/etc/profile.d/conda.sh
conda activate utdq

python /groups/igonin/ecastillo/utdquake/test/07082026/fix_das_bank.py

echo "✅ DONE"