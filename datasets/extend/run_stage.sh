#!/bin/bash
#SBATCH -N 1
#SBATCH -n 4
#SBATCH --mem=64G
#SBATCH -p normal
#SBATCH --time=2-00:00:00
# Process the new events of networks (python -m utdquake.extend stations / stage), one after the other.
# MODE: stations (coordinates of the new stations: one job only, the stations.csv cache is shared), stage
# (station distances, pick QC, tables: one network per database, so several jobs can run at once), or both.
# A failed network is reported and the next one goes on. STAGED_SINCE=<date>: networks staged since then are
# skipped (to rerun a group after a fix).
#   L=$UTDQUAKE_ROOT/.utdquake/extend/v2.0/logs
#   sbatch -J stations -o $L/%x_%j.out run_stage.sh stations v2.0 ETH GEOFON ...
#   sbatch -J stage_1 -o $L/%x_%j.out run_stage.sh stage v2.0 ETH GEOFON ...
MODE=$1; VERSION=$2; shift 2
REPO=${UTDQ_REPO:-/groups/igonin/ecastillo/utdquake}
source /groups/igonin/ecastillo/anaconda3/etc/profile.d/conda.sh
conda activate utdq
export UTDQUAKE_ROOT=${UTDQUAKE_ROOT:-/groups/igonin/ecastillo/UTDQuake} HF_HUB_OFFLINE=1 PYTHONPATH=$REPO
cd $REPO
echo "$(date) $MODE $VERSION: $*; code $REPO"
failed=()
for NET in "$@"; do
    echo "$(date) $NET"
    if [ "$MODE" != stage ]; then
        python -W ignore -m utdquake.extend stations $VERSION $NET > >(tail -3) || { failed+=("$NET:stations"); continue; }
    fi
    if [ "$MODE" != stations ]; then
        if [ -n "${STAGED_SINCE:-}" ] && python -c "
import json, sys; p = '$UTDQUAKE_ROOT/.utdquake/extend/$VERSION/$NET.json'
log = json.load(open(p))
sys.exit(0 if any(e.get('step') == 'stage' and e['date'] >= '$STAGED_SINCE' for e in log) else 1)"; then
            echo "$NET staged since $STAGED_SINCE: skipped"; continue
        fi
        python -W ignore -m utdquake.extend stage $VERSION $NET || failed+=("$NET:stage")
    fi
done
echo "$(date) done; failed: ${failed[*]:-none}"
[ ${#failed[@]} -eq 0 ]
