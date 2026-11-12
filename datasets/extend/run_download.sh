#!/bin/bash
#SBATCH -N 1
#SBATCH --cpus-per-task=8
#SBATCH --mem=48G
#SBATCH -p normal
#SBATCH -t 2-00:00:00
# Download the new events of an extension (python -m utdquake.extend run): every incomplete network of the
# given providers, PARALLEL per provider at a time (1: providers limit the request rate). When the time limit is near it stops starting networks; the next
# job is queued at the start (after this one, however it ends: a network still running at the time limit is
# killed, and continued by the next job from its bank) and cancelled when every network is complete or the
# run fails (see datasets/extend/README.md).
#
#   L=$UTDQUAKE_ROOT/.utdquake/extend/v2.0/logs   # the log folder of the version (made by the first job)
#   sbatch -J ext_ISC -o $L/%x_%j.out run_download.sh v2.0 ISC 1 1
#   sbatch -J ext_USGS -o $L/%x_%j.out run_download.sh v2.0 USGS,ETH,GEOFON 1 2
VERSION=${1:?version} PROVIDERS=${2:?providers} PARALLEL=${3:-1} WORKERS=${4:-2}
source /groups/igonin/ecastillo/anaconda3/etc/profile.d/conda.sh
conda activate utdq
REPO=${UTDQ_REPO:-/groups/igonin/ecastillo/utdquake}
export PYTHONPATH=$REPO UTDQUAKE_ROOT=${UTDQUAKE_ROOT:-/groups/igonin/ecastillo/UTDQuake} HF_HUB_OFFLINE=1
LOGS=$UTDQUAKE_ROOT/.utdquake/extend/$VERSION/logs
mkdir -p "$LOGS"
echo "$(date) $VERSION $PROVIDERS parallel $PARALLEL workers $WORKERS; code $REPO ($(git -C $REPO rev-parse --short HEAD))"
next=$(sbatch --parsable --export=ALL --dependency=afterany:$SLURM_JOB_ID -J "$SLURM_JOB_NAME" \
       -o "$LOGS/%x_%j.out" "$REPO/datasets/extend/run_download.sh" "$@")
echo "$(date) next job queued: $next"
python -W ignore -m utdquake.extend run $VERSION --provider $PROVIDERS --parallel $PARALLEL --workers $WORKERS --hours 46
code=$?
if [ $code -eq 3 ]; then
    echo "$(date) networks left: continued by $next"
else
    scancel "$next"
    echo "$(date) next job $next cancelled"
fi
echo "$(date) DONE (exit $code)"
