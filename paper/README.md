# Paper figures

Figures of the UTDQuake paper, for each dataset version:

| Folder | Data |
|---|---|
| `v1/` | UTDQuake **v1.0** as published (Hugging Face tag `v1.0`, a local copy in `UTDQuake_paper_v1`) |
| `v2/` | UTDQuake **v2** (the working copy `UTDQuake`: v2.0 and the corrections listed under v2.1 in `docs/source/versions.rst`) |

Each version folder has the same figures (logs of the last run in `logs/`):

| File | Figure | Made with |
|---|---|---|
| `utdq_overview.png` | earthquakes above stations, world maps with their counts | `Dataset.plot_global_overview(layout="vertical")` |
| `utdq_overview_stats.png` | the same maps side by side, and the 5 statistics panels below (docs: home page, versions page) | `Dataset.plot_global_overview(layout="combined")` |
| `utdq_stats.png` | depth, magnitude, azimuthal gap, epicentral distance by phase, arrival azimuth | `Dataset.plot_stats` |
| `utdq_density.png` | stations against area of every network, by continent; research catalogs (`R..`) as hollow circles | `Dataset.plot_network_station_density` |
| `utdq_magnitude.png` | phase and station counts by magnitude | `Dataset.plot_phase_count_radar_by_magnitude` |
| `utdq_travel_time.png`, `utdq_z_score.png` | travel times and their z-scores | see the scripts |
| `utdq_das.png` | the DAS network (UWF; the same data in every version) | `scripts/utdq_das.py` |

## Making them

The code is in `scripts/` (`_local.py` chooses the version and its local data; every script writes to
`paper/<version>/`):

```bash
cd paper
sbatch --export=ALL,PAPER_VERSION=v1 -o v1/logs/utdq_figures_%j.out scripts/utdq_figures.sh
sbatch --export=ALL,PAPER_VERSION=v2 -o v2/logs/utdq_figures_%j.out scripts/utdq_figures.sh
# some figures only: ... scripts/utdq_figures.sh utdq_stats utdq_density
```

The docs figures (`figures/` at the repo root) are made by `datasets/hf_release/overview_figures.py`; the
versions page copies `v1/` and `v2/` `utdq_overview_stats.png`.
