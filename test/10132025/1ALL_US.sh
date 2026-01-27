#!/bin/bash
#SBATCH -N 1                
#SBATCH -n 64              
#SBATCH -p normal            
#SBATCH -J ALLUS      
#SBATCH -o /groups/igonin/ecastillo/UTDQuake/test/10132025/1ALL_US.out

source /groups/igonin/ecastillo/anaconda3/etc/profile.d/conda.sh
conda activate utdq

python /groups/igonin/ecastillo/UTDQuake/test/10132025/1.download_events_US.py
