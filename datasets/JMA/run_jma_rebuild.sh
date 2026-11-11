#!/bin/bash
#SBATCH -N 1
#SBATCH -n 4
#SBATCH --mem=48G
#SBATCH -p normal
#SBATCH -J jma_rebuild
#SBATCH --time=24:00:00
#SBATCH -o /groups/igonin/ecastillo/utdquake_v2ext/datasets/JMA/logs/%x_%j.out
# JMA from scratch: the previous JMA banks and stage output are moved aside (QUAR), then extend (new events),
# replace-v1 (v1 events with all their picks), combine (one bank) and the stage step.
set -e
source /groups/igonin/ecastillo/anaconda3/etc/profile.d/conda.sh
conda activate utdq
export PYTHONPATH=/groups/igonin/ecastillo/utdquake_v2ext UTDQUAKE_ROOT=/groups/igonin/ecastillo/UTDQuake_v2 HF_HUB_OFFLINE=1
W=$UTDQUAKE_ROOT/.utdquake/extend/v2.0; S=$W/stage; QUAR=$W/quarantine_JMA_$(date +%Y%m%d_%H%M)
mkdir -p $QUAR
for p in banks/JMA banks/JMA_v1; do [ -e $W/$p ] && mkdir -p $QUAR/raw && mv $W/$p $QUAR/raw/; done
for p in banks/JMA .utdquake/export/db/events/JMA.db .utdquake/export/db/picks/JMA.db .utdquake/export/db/stations/JMA.db \
         .utdquake/export/db/stations/.JMA .utdquake/export/manifests/events/utdq_net=JMA.parquet \
         .utdquake/export/manifests/picks/utdq_net=JMA.parquet .utdquake/export/manifests/stations/utdq_net=JMA.parquet; do
    [ -e $S/$p ] && mkdir -p $QUAR/stage/$(dirname $p) && mv $S/$p $QUAR/stage/$p
done
echo "$(date) old JMA moved to $QUAR"
cd /groups/igonin/ecastillo/utdquake_v2ext/datasets/JMA
for step in extend replace-v1 combine; do echo "$(date) $step"; python -W ignore jma_to_utdq.py $step | tail -12; done
echo "$(date) stage"
cd /groups/igonin/ecastillo/utdquake_v2ext && python -W ignore -m utdquake.extend stage v2.0 JMA | tail -15
echo "$(date) DONE"
