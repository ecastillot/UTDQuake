#!/bin/bash
#SBATCH -N 1
#SBATCH -n 1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH -p normal
#SBATCH -J colab_check
#SBATCH --time=06:00:00
# Runs the two Colab notebooks (examples/*.ipynb) as a new user would: a fresh virtual environment with
# utdquake from PyPI, an empty HOME (no UTDQuake or Hugging Face cache), every cell executed. The executed
# copies go to $WORK/out (the notebooks in examples/ stay without outputs). Only the publish cell is not run
# (it is commented out in the notebook).
#   sbatch -o /groups/igonin/ecastillo/colab_check/colab_check_%j.out run_colab_check.sh
set -u
REPO=/groups/igonin/ecastillo/utdquake
WORK=/groups/igonin/ecastillo/colab_check
mkdir -p $WORK/out $WORK/home
export HOME=$WORK/home MPLBACKEND=Agg
unset UTDQUAKE_ROOT UTDQUAKE_DAS_ROOT PYTHONPATH HF_HUB_OFFLINE
source /groups/igonin/ecastillo/anaconda3/etc/profile.d/conda.sh
conda activate utdq                       # only for its python: the venv below has no access to its packages
python -m venv $WORK/venv && source $WORK/venv/bin/activate
pip install -q --upgrade pip
pip install -q utdquake cartopy nbconvert ipykernel
python -c "import utdquake; print('utdquake', utdquake.__version__)"
cd $WORK/out
status=0
for nb in UTDQuake_Access UTDQuake_Upload; do
    echo "$(date +%T) running $nb"
    if jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=3600 \
         --output $WORK/out/$nb.ipynb $REPO/examples/$nb.ipynb; then
        echo "  $nb OK"
    else
        echo "  $nb FAILED"; status=1
    fi
done
echo "$(date) DONE (status $status)"
exit $status
