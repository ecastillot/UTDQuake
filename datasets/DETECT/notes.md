# DETECT (R10)

- Catalog: Scotto di Uccio et al. (2025), Zenodo 10.5281/zenodo.15372023 (CC BY 4.0), version of 2025-05-09
  (the only one). Network paper: ESSD 18, 7751 (2026), 10.5194/essd-18-7751-2026.
- Stations: GEOFON network ZK, 200 stations S0101-S1020 (`raw/zk_channels.txt`, fdsnws-station
  level=channel, downloaded 2026-11-04). Coordinates are the same in every epoch. Waveforms public
  (embargo over).
- Raw: 3,653 events (Sep 2021 - Jul 2022), 46,710 P + 71,423 S picks on 195 stations. No event ids, no
  channels, no pick uncertainties; picks matched to events by row.
- Picks are automatic (EQTransformer + EQCorrscan); location method not described in the ESSD paper
  (the catalog paper, Scotto di Uccio et al. 2026, is cited but not public on 2026-11-04).

## Events dropped before QC

| reason | events |
|---|---|
| no location | 38 |
| origin time on a whole second (ms 000/001/999) | 599 (637 with the unlocated ones) |
| above the surface (depth < -elevation of the nearest station) | 141 |
| kept | 2,875 |

Whole-second origins: travel-time residuals against a linear distance fit of the other events
(3-60 km): P median per-event residual +0.75 s (IQR 0.39-1.13), S +0.86 s, against 0.00 s for the
events with milliseconds. The origin times are rounded/shifted, so their travel times would be biased
(as LASSO's GENIE origins). They are concentrated in Sep 2021 - Feb 2022.

Above the surface: depths piled up at -2.0 km (30 events), the top of a location grid; depth taken as km
below sea level.

Kept as they are: 3 events deeper than 30 km (two at ~80 km under array 2, 22-25 picks each); the UTDQuake
QC and the travel-time z-scores apply as for every network.

## Events sharing picks

A pick can belong to one event only (the bank refuses arrivals linked to a pick of another event).
13 pairs of consecutive events share picks: 8 are the same event listed twice (origins < 1 s apart,
sharing at least half of the smaller event's picks; the one with fewer picks is dropped), 5 are
different events with a few shared picks (2-15; removed from the event with fewer picks, 37 picks).
Result: 2,867 events, 101,062 picks (39,515 P, 61,547 S) before the UTDQuake QC.

## Travel times and figures

The build ends with the travel-time model and z-scores (build_travel_time_model, update_picks=True),
the stats cache and the standard figure set (figures/networks/R10), as every network before upload.
