#!/bin/bash
#SBATCH -N 1                
#SBATCH -n 64              
#SBATCH -p normal            
#SBATCH -J ALL      
#SBATCH -o /groups/igonin/ecastillo/UTDQuake/test/10132025/ALL_specific.out

source /groups/igonin/ecastillo/anaconda3/etc/profile.d/conda.sh
conda activate utdq

python /groups/igonin/ecastillo/UTDQuake/test/10132025/1.download_specific_events.py