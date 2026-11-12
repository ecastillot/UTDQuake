#!/bin/bash
#SBATCH -N 1
#SBATCH -n 4
#SBATCH --mem=96G
#SBATCH -p normal
#SBATCH --time=1-00:00:00
# Fixes after the merge (utdquake.extend restore_v1_picks / normalize_phases), then the merge validation.
#   RESTORE="HEL OTT" sbatch -J fix -o $L/%x_%j.out run_fix.sh v2.0 NET [NET ...]
# RESTORE: networks whose v1 events without picks are processed again from the v1 bank; then the phases of
# every NET are normalized (PG -> Pg, ...) and every NET is validated against the merge backups.
VERSION=$1; shift
REPO=${UTDQ_REPO:-/groups/igonin/ecastillo/utdquake}
source /groups/igonin/ecastillo/anaconda3/etc/profile.d/conda.sh
conda activate utdq
export UTDQUAKE_ROOT=${UTDQUAKE_ROOT:-/groups/igonin/ecastillo/UTDQuake} HF_HUB_OFFLINE=1 PYTHONPATH=$REPO
cd $REPO
set -o pipefail
echo "$(date) restore v1 picks: ${RESTORE:-none}"
if [ -n "${RESTORE:-}" ]; then
    python -W ignore -m utdquake.extend restore_v1_picks $VERSION $RESTORE 2>&1 | grep -vE "INFO|WARNING" | tail -80 || exit 1
fi
echo "$(date) normalize phases: $*"
python -W ignore -m utdquake.extend normalize_phases $VERSION "$@" 2>&1 | grep -E '"renamed"|Error|Traceback' || exit 1
echo "$(date) validate"
python -W ignore $REPO/datasets/extend/tests/validate_merge.py $UTDQUAKE_ROOT $VERSION "$@"
rc=$?
echo "$(date) done rc=$rc"
exit $rc
