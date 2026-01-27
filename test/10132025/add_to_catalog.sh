#!/bin/bash
#SBATCH -N 1                
#SBATCH -n 64              
#SBATCH -p normal            
#SBATCH -J add2cat     
#SBATCH -o /groups/igonin/ecastillo/UTDQuake/test/10132025/add_to_catalog.out

source /groups/igonin/ecastillo/anaconda3/etc/profile.d/conda.sh
conda activate utdq

python /groups/igonin/ecastillo/UTDQuake/test/10132025/add_to_catalog.py