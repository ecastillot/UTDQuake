#!/bin/bash
#SBATCH -N 1
#SBATCH -n 4
#SBATCH --mem=96G
#SBATCH -p normal
#SBATCH --time=1-00:00:00
# Merge the staged networks of a version into the UTDQuake tables (python -m utdquake.extend merge), one
# network per process. The tables are backed up first (<root>/.utdquake/backups/<version>_merge/), the merge is
# idempotent, and a failed network is reported and the next one goes on.
#   L=$UTDQUAKE_ROOT/.utdquake/extend/v2.0/logs
#   sbatch -J merge -o $L/%x_%j.out run_merge.sh v2.0 ETH JMA ci ...
VERSION=$1; shift
REPO=${UTDQ_REPO:-/groups/igonin/ecastillo/utdquake}
source /groups/igonin/ecastillo/anaconda3/etc/profile.d/conda.sh
conda activate utdq
export UTDQUAKE_ROOT=${UTDQUAKE_ROOT:-/groups/igonin/ecastillo/UTDQuake} HF_HUB_OFFLINE=1 PYTHONPATH=$REPO
cd $REPO
echo "$(date) merge $VERSION into $UTDQUAKE_ROOT: $*; code $REPO"
failed=()
for NET in "$@"; do
    echo "$(date) $NET"
    python -W ignore -m utdquake.extend merge $VERSION $NET 2>&1 | grep -vE "INFO" | tail -40 \
        ; [ ${PIPESTATUS[0]} -eq 0 ] || failed+=("$NET")
done
echo "$(date) done; failed: ${failed[*]:-none}"
[ ${#failed[@]} -eq 0 ]
