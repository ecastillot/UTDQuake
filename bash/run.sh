#!/bin/bash
#SBATCH -N 1                
#SBATCH -n 64              
#SBATCH -p normal            
#SBATCH -J test             
#SBATCH -o /groups/igonin/ecastillo/UTDQuake/bash/my_python_job.out

source conda activate utdq

python /groups/igonin/ecastillo/UTDQuake/project/stations/2.plot_stats.py
