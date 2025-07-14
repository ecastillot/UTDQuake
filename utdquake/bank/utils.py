# /**
#  * @author Emmanuel Castillo
#  * @email [castillo.280997@gmail.com]
#  * @create date 2025-05-24 14:31:48
#  * @modify date 2025-05-24 14:31:48
#  * @desc [description]
#  */
import os
import datetime
import logging
import obsplus
import warnings
import sqlite3
import pandas as pd
from obspy.clients.fdsn import Client as FDSNClient 
import numpy as np
from obspy import UTCDateTime, Catalog
from typing import  Optional
from obspy.clients.fdsn.header import URL_MAPPINGS
import matplotlib.pyplot as plt
import matplotlib.cm as cm
from obspy.geodetics import gps2dist_azimuth, kilometer2degrees

warnings.filterwarnings("ignore", category=UserWarning, module="obspy.io.quakeml.core")

logger = logging.getLogger(__name__)

OTHER_MAPPINGS = {
        "IRIS": "https://service.iris.edu", #USA
        "NIED": "http://www.fnet.bosai.go.jp",
        "EIDA2": "https://eida.orfeus-eu.org",
        "SED": "https://eida.ethz.ch",
        "GEOFON": "https://geofon.gfz-potsdam.de",
        "INGV": "https://webservices.ingv.it",
        "NRCan": "https://earthquakes.canada.ca",
        "CSN": "https://csn.uchile.cl",
        "GeoNet": "https://service.geonet.org.nz",
        "RESIF": "https://ws.resif.fr",
        "IIEES": "http://ws.iiees.ac.ir",
        "SSN": "https://ssn.unam.mx",
        "ISC": "http://isc-mirror.iris.washington.edu"
    }
def standardize_phases(df: pd.DataFrame) -> pd.DataFrame:
    """
    For each network-station pair, keep only one P and one S.
    Rename Pg, Pn, etc. to P if no explicit P exists.
    Pick the earliest arrival for each.
    """
    # Identify P-type and S-type phases
    P_phases = ['P', 'Pg', 'Pn', 'Pb']
    S_phases = ['S', 'Sn', 'Sg']

    def keep_first_P_S(group):
        # Filter for P-type and S-type
        p_group = group[group['phase'].isin(P_phases)]
        s_group = group[group['phase'].isin(S_phases)]

        selected = []

        # Handle P
        if not p_group.empty:
            # If explicit P exists, keep only it
            if 'P' in p_group['phase'].values:
                p_group = p_group[p_group['phase'] == 'P']
            # Take earliest by time
            first_p = p_group.loc[p_group['time'].idxmin()]
            first_p = first_p.copy()
            first_p['phase'] = 'P'
            selected.append(first_p)

        # Handle S
        if not s_group.empty:
            if 'S' in s_group['phase'].values:
                s_group = s_group[s_group['phase'] == 'S']
            first_s = s_group.loc[s_group['time'].idxmin()]
            first_s = first_s.copy()
            first_s['phase'] = 'S'
            selected.append(first_s)

        return pd.DataFrame(selected)

    cleaned = df.groupby(['origin_id','network', 'station'], group_keys=False).apply(keep_first_P_S)

    return cleaned.reset_index(drop=True)
    
def merge_arrivals_and_picks(
    arrivals: pd.DataFrame,
    picks: pd.DataFrame,
    picks_subset_columns: list = ['time']
) -> pd.DataFrame:
    """
    Merge arrivals with a subset of columns from picks, using 'seed_id'.
    Keeps all arrival columns plus the specified columns from picks.

    :param arrivals: DataFrame with arrival info.
    :param picks: DataFrame with pick info.
    :param picks_subset_columns: List of column names from picks to keep (default is ['time']).
    :return: Merged DataFrame.
    """
    # Always include 'resource_id' for the join
    picks_subset = picks[['resource_id'] + picks_subset_columns]
    # picks_subset = picks[picks_subset_columns]

    merged = pd.merge(
                arrivals,
                picks_subset,
                left_on='pick_id',     # column in arrivals
                right_on='resource_id', # column in picks
                how='inner',             # or 'left', 'right', 'outer'
                suffixes=('_arrival', '_pick')   # suffix for overlapping columns
            )
    

    return merged

def analysis_to_df(analysis: dict) -> pd.DataFrame:
    """
    Flatten the analysis dictionary into a single-row DataFrame,
    excluding 'stations_data'.

    Parameters
    ----------
    analysis : dict
        The analysis dictionary.

    Returns
    -------
    pd.DataFrame
        A single-row DataFrame with flattened keys.
    """
    flat_data = {}

    for key, values in analysis.items():
        if key == 'stations_data':
            continue
        for subkey, value in values.items():
            col_name = f"{key}_{subkey}"
            flat_data[col_name] = value

    return pd.DataFrame([flat_data])

def parse_catalog(catalog,stations=None,to_df=False):
    """
    Parse a seismic catalog, merge arrivals with picks and stations,
    standardize phases, and produce summary statistics.

    Parameters
    ----------
    catalog : Catalog object
        Seismic catalog containing events, arrivals, and picks.
    stations : DataFrame or None,optional
        Station metadata to merge with arrivals.
    to_df : bool, optional
        If True, converts the final analysis dictionary to a DataFrame.

    Returns
    -------
    dict or DataFrame
        Summary statistics of events, arrivals, and stations.
    """

    total_events = len(catalog.events)

    arrival_dict = {}
    arrivals = catalog.arrivals_to_df()
    picks = catalog.picks_to_df()

    logger.info(f"Initial total events in catalog: {total_events} ")
    logger.info(f"Arrivals: {len(arrivals)} | Picks: {len(picks)} -- Initially")

    # removing duplicates based on 'seed_id'
    arrivals = arrivals.drop_duplicates(subset=['resource_id'])
    picks = picks.drop_duplicates(subset=['resource_id'])


    logger.info(f"Arrivals: {len(arrivals)} | Picks: {len(picks)} -- After drop duplicates")


    # merge arrivals with picks to extract time
    arrivals = merge_arrivals_and_picks(arrivals, picks)

    logger.info(f"Arrivals: {len(arrivals)} | Picks: {len(picks)} -- After merge arrivals with picks")

    # standardize phases
    # This will keep only one P and one S for each network-station pair
    arrivals = standardize_phases(arrivals)
    logger.info(f"Arrivals: {len(arrivals)} -- After standardize phases (keep only one P and one S)")

    # arrival analysis
    total_arrivals = len(arrivals)
    total_p_arrivals = len(arrivals[arrivals['phase'].isin( ['P'])])
    total_s_arrivals = len(arrivals[arrivals['phase'].isin(['S'])])

    arrival_dict['total_arrivals'] = total_arrivals
    arrival_dict['total_p_arrivals'] = total_p_arrivals
    arrival_dict['total_s_arrivals'] = total_s_arrivals

    if stations is None:
        analysis = {
            "events": {"total": total_events},
            "arrivals": {
                "total": total_arrivals,
                "good": np.nan,  # all arrivals are considered good if no stations
                "bad": np.nan},
            "p_arrivals": {
                "total": total_p_arrivals,
                "good": np.nan,  # all arrivals are considered nan
                "bad": np.nan},
            "s_arrivals": {
                "total": total_s_arrivals,
                "good": np.nan,  # all arrivals are considered nan
                "bad": np.nan},
            "stations": {"total": 0, "good": 0, "bad": 0},
            "stations_data": {"good": pd.DataFrame(), "bad": pd.DataFrame()}}
        return analysis_to_df(analysis) if to_df else analysis

    stations = stations.drop_duplicates(subset=['network', 'station'],
                                            ignore_index=True)
    arrivals_with_stations = arrivals.merge(
                                            stations[['network', 'station','latitude', 'longitude','elevation']],
                                            on=['network', 'station'], 
                                            how='left')

    logger.info(f"Arrivals: {len(arrivals_with_stations)} -- After merge arrivals with stations")


    gd_arrivals_mask = arrivals_with_stations[['latitude', 'longitude']].notna().all(axis=1)
    gd_arrivals = arrivals_with_stations[gd_arrivals_mask]
    total_gd_arrivals = len(gd_arrivals)
    total_p_gd_arrivals = len(gd_arrivals[gd_arrivals['phase'].isin(['P'])])
    total_s_gd_arrivals = len(gd_arrivals[gd_arrivals['phase'].isin(['S'])])

    total_bad_arrivals = total_arrivals - total_gd_arrivals
    total_bad_p_arrivals = total_p_arrivals - total_p_gd_arrivals
    total_bad_s_arrivals = total_s_arrivals - total_s_gd_arrivals

    # Summary of arrivals
    logger.info(f"Summary of arrivals for {total_events} events:")
    logger.info(f"Total arrivals: {total_arrivals} -- Good arrivals: {total_gd_arrivals} -- Bad arrivals: {total_bad_arrivals}")
    logger.info(f"P arrivals: {total_p_arrivals} -- Good P arrivals: {total_p_gd_arrivals} -- Bad P arrivals: {total_bad_p_arrivals}")
    logger.info(f"S arrivals: {total_s_arrivals} -- Good S arrivals: {total_s_gd_arrivals} -- Bad S arrivals: {total_bad_s_arrivals}")

    stations_with_arrivals = arrivals_with_stations.drop_duplicates(subset=['network', 'station'])
    total_stations = len(stations_with_arrivals)
    bad_stations_mask = stations_with_arrivals[['latitude', 'longitude']].isna().any(axis=1)
    bad_stations = stations_with_arrivals[bad_stations_mask]
    gd_stations = stations_with_arrivals[~bad_stations_mask]
    total_bad_stations = len(bad_stations)
    total_gd_stations = len(gd_stations)

    # Summary of stations
    logger.info(f"Summary of stations for {total_events} events:")
    logger.info(f"Total stations: {total_stations} -- Good stations: {total_gd_stations} -- Bad stations: {total_bad_stations}")

    analysis = {}
    analysis['events'] = {"total": total_events}
    analysis['arrivals'] = {
        "total": total_arrivals,
        "good": total_gd_arrivals,
        "bad": total_bad_arrivals}
    analysis['p_arrivals'] = {
        "total": total_p_arrivals, 
        "good": total_p_gd_arrivals,
        "bad": total_bad_p_arrivals}
    analysis['s_arrivals'] = {
        "total": total_s_arrivals,
        "good": total_s_gd_arrivals,
        "bad": total_bad_s_arrivals}
    analysis['stations'] = {
        "total": total_stations,
        "good": total_gd_stations,
        "bad": total_bad_stations}
    analysis['stations_data'] = {
        "good": gd_stations,
        "bad": bad_stations
        }

    if to_df:
        analysis = analysis_to_df(analysis)

    # test = analysis["stations_data"]["good"].drop_duplicates(subset=['network', 'station'])

    # # test_stations = test_arrivals[test_arrivals[["network", "station"]].apply(tuple, axis=1).isin(test[["network", "station"]].apply(tuple, axis=1))]
    # test_stations = test_arrivals[test_arrivals[["network", "station"]].apply(tuple, axis=1).isin([("GO","SHNK"),("AU","MTN")])]
    # # print(test_stations[['network', 'station']].head(10))

    # print(f"testing arrivals with stations: IM GO AU")
    # print(test_stations)
    # print(test_arrivals[test_arrivals["network"].isin(["IM","GO","AU"])])

    # fig = plt.figure(figsize=(10, 8))
    # ax = fig.add_subplot()

    # # Basic scatter plot
    # ax.scatter(test['longitude'], test['latitude'], color='red', s=50, marker='^')

    # # Add labels (NO transform needed!)
    # for _, row in test.iterrows():
    #     ax.text(row['longitude'] + 0.05, row['latitude'] + 0.05, row["network"] +"."+ row['station'], fontsize=9)

    # ax.set_xlabel("Longitude")
    # ax.set_ylabel("Latitude")
    # ax.set_title("Station Map")

    # fig.savefig(os.path.join(output_dir, "stations_map.png"), dpi=300)
    # print("plotted")
    # print(arrivals_with_stations[['network', 'station', 'latitude', 'longitude']].head(10))


    return analysis

def initialize_stations_db(db_path):
    """
    Initialize the stations database with the proper table and primary key.

    Parameters
    ----------
    db_path : str
        Path to the SQLite database file.

    Notes
    -----
    This function creates the 'stations_index' table with a primary key on
    'seed_id' to ensure inserts with the same seed_id will overwrite existing rows.
    """
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stations_index (
                network TEXT,
                station TEXT,
                location TEXT,
                channel TEXT,
                seed_id TEXT PRIMARY KEY,
                latitude REAL,
                longitude REAL,
                elevation REAL,
                depth REAL,
                azimuth REAL,
                dip REAL,
                sample_rate REAL,
                start_date TEXT,
                end_date TEXT
            )
        """)
        conn.commit()

def load_stations_metadata_from_bank(db_path):
    """
    Loads the station metadata database stored in a SQLite file.

    Parameters
    ----------
    db_path : str
        Path to the .stations.db SQLite database file.

    Returns
    -------
    df : pandas.DataFrame
        DataFrame containing the station metadata.
    """
    if not os.path.exists(db_path):
        logger.error(f"Database file not found: {db_path}")
        raise FileNotFoundError(f"Database file not found: {db_path}")

    try:
        with sqlite3.connect(db_path) as conn:
            logger.info(f"Loading stations from database: {db_path}")
            df = pd.read_sql("SELECT * FROM 'stations_index'", conn)
            df["location"] = df["location"].astype(str).str.zfill(2)
            logger.info(f"Loaded {len(df)} stations from database.")
    except Exception as e:
        logger.error(f"Failed to load stations from database: {e}")
        raise RuntimeError(f"Failed to load stations from database: {e}")

    return df

def update_starttime_from_bank(ebank, starttime, endtime, max_n_events=None):
    """
    Update starttime based on the last event in the event bank index.

    Parameters
    ----------
    ebank : EventBank
        An event bank object with a read_index() method.
    starttime : datetime.datetime
        The original start time.
    endtime : datetime.datetime
        The end time for the query.
    max_n_events : int or None, optional
        Maximum number of events to keep in the bank.

    Returns
    -------
    tuple
        (new_starttime, total_events) or (None, total_events) if no update is needed.
    """
    if max_n_events is None:
        logger.warning(
            "max_n_events is None. "
            "This will download all events from the event bank."
        )

    archive_bank = ebank.read_index()
    total_events = len(archive_bank)
    logger.info("Total events in archive bank: %d", total_events)

    if total_events > max_n_events:
        logger.info(
            "Event bank already has %d events, which exceeds max_n_events=%d. "
            "Skipping download.",
            total_events,
            max_n_events
        )
        return None, total_events

    if not archive_bank.empty:
        last_event_time = archive_bank['time'].max()
        new_starttime = last_event_time + datetime.timedelta(seconds=1)
        logger.info(
            "Setting starttime to %s based on last event in bank.",
            new_starttime
        )

        if new_starttime >= endtime:
            logger.error(
                "Start time %s is after end time %s. No events will be downloaded.",
                new_starttime,
                endtime
            )
            return None, total_events

        return new_starttime, total_events

    logger.info("Event bank is empty, starting from original starttime.")
    return starttime, total_events

def process_origin_arrivals(origin, df_stations, bad_inv_data, event_id):
    """
    Process all arrivals in a single origin to:
      - Compute distance (in degrees) and azimuth from origin to station
      - Populate Origin.quality metadata in a single pass

    Parameters
    ----------
    origin : obspy.core.event.Origin
        The origin object containing associated arrivals to process.
    df_stations : pandas.DataFrame
        DataFrame with station metadata containing columns:
        ['network', 'station', 'latitude', 'longitude'].
    bad_inv_data : list of dict
        A list to store metadata about arrivals with missing or invalid station info.
    event_id : str, optional
        The event ID to associate with metadata entries. 

    Returns
    -------
    None
        Modifies the `origin` in-place and appends errors to `bad_inv_data`.
    """
    olat, olon = origin.latitude, origin.longitude
    arrivals = origin.arrivals

    distances = []
    esazs = []
    stations_used = set()
    used_phase_count = 0

    logger.debug(f"Processing origin {origin.resource_id.id} with {len(arrivals)} arrivals")

    for arrival in arrivals:
        pick = arrival.pick_id.get_referred_object()
        net = pick.waveform_id.network_code
        sta = pick.waveform_id.station_code

        logger.debug(f"Processing arrival for {net}.{sta}")
        df_sta = df_stations[
            (df_stations.network == net) & (df_stations.station == sta)
        ]

        if df_sta.empty:
            logger.warning(f"Missing station metadata for {net}.{sta} in origin {origin.resource_id.id}")
            bad_inv_data.append({
                "network": net,
                "station": sta,
                "origin_id": origin.resource_id.id,
                "event_id": event_id,
                "error": "No station data found"
            })
            continue


        try:
            slat, slon = df_sta[["latitude", "longitude"]].values[0]
            dist_m, _, esaz = gps2dist_azimuth(slat, slon, olat, olon)
            dist_deg = kilometer2degrees(dist_m * 1e-3)

            arrival.distance = dist_deg
            arrival.azimuth = esaz

            distances.append(dist_deg)
            esazs.append(esaz)
            stations_used.add((net, sta))

            if arrival.time_weight is None or arrival.time_weight > 0:
                used_phase_count += 1
        

        except Exception as e:
            logger.error(f"Error processing {net}.{sta} in origin {origin.resource_id.id}: {e}")
            bad_inv_data.append({
                "network": net,
                "station": sta,
                "event_id": origin.resource_id.id,
                "error": "Invalid lat/lon or processing failure"
            })

    # Update Origin.quality metadata
    quality = origin.quality
    quality.associated_phase_count = len(arrivals)
    quality.used_phase_count = used_phase_count
    quality.used_station_count = len(stations_used)

    if distances:
        quality.minimum_distance = min(distances)
        quality.maximum_distance = max(distances)
        quality.median_distance = float(np.median(distances))
        logger.debug(f"Updated distance metrics for origin {origin.resource_id.id}")

    if len(esazs) >= 2:
        esazs = sorted(set(esazs))
        gaps = [esazs[i+1] - esazs[i] for i in range(len(esazs)-1)]
        gaps.append(360 - esazs[-1] + esazs[0])

        quality.azimuthal_gap = max(gaps)
        if len(gaps) >= 2:
            quality.secondary_azimuthal_gap = sorted(gaps)[-2]

        logger.debug(f"Updated azimuthal gaps for origin {origin.resource_id.id}")
    

def append_stations_to_catalog(catalog: Catalog, df_stations) -> tuple[Catalog, pd.DataFrame]:
    """
    Append distance and azimuth to each arrival in a catalog,
    and update Origin.quality metadata for each event.

    Parameters
    ----------
    catalog : obspy.core.event.Catalog
        Catalog object containing events and arrivals.
    df_stations : pandas.DataFrame
        DataFrame containing station metadata with columns:
        ['network', 'station', 'latitude', 'longitude'].

    Returns
    -------
    catalog : obspy.core.event.Catalog
        Modified catalog with distance, azimuth, and quality metrics added.
    bad_inv_data_df : pandas.DataFrame
        DataFrame listing arrivals with missing or invalid station metadata.
    """
    bad_inv_data = []

    logger.info(f"Starting to process {len(catalog.events)} events in catalog.")

    for event in catalog:
        origin = event.preferred_origin() or (event.origins[0] if event.origins else None)

        if origin is None:
            logger.warning(f"Event {event.resource_id.id} has no origin. Skipping.")
            continue

        logger.info(f"Processing event {event.resource_id.id} with origin {origin.resource_id.id}")
        process_origin_arrivals(origin, df_stations, bad_inv_data,event.resource_id.id)

    bad_inv_data_df = pd.DataFrame(bad_inv_data)

    logger.info("Finished processing catalog.")
    if not bad_inv_data_df.empty:
        logger.warning(f"{len(bad_inv_data_df)} stations had missing/invalid metadata.")

    return catalog, bad_inv_data_df

def extend_fdsn_url_mappings(additional_mappings: Optional[dict] = None) -> dict:
    """
    Extend the global URL_MAPPINGS dictionary with new entries from additional_mappings.

    If no additional mappings are provided, the function uses OTHER_MAPPINGS by default.
    It adds only those entries whose keys (case-insensitive) do not already exist in 
    URL_MAPPINGS.

    Parameters
    ----------
    additional_mappings : dict, optional
        Dictionary of new FDSN provider name to URL mappings to be added. If None,
        OTHER_MAPPINGS will be used.

    Returns
    -------
    dict
        The updated URL_MAPPINGS dictionary including any new entries.
    """
    # Use OTHER_MAPPINGS by default if no input is provided
    if additional_mappings is None:
        additional_mappings = OTHER_MAPPINGS.copy()
    else:
        # Merge OTHER_MAPPINGS and additional_mappings, giving priority to the latter
        additional_mappings = OTHER_MAPPINGS | additional_mappings

    # Normalize the existing keys in URL_MAPPINGS for case-insensitive comparison
    url_mappings_keys = [k.lower() for k in URL_MAPPINGS.keys()]

    # Iterate through the provided additional mappings
    for key, url in additional_mappings.items():
        # Add the new mapping if the key (case-insensitive) does not already exist
        if key.lower() not in url_mappings_keys:
            URL_MAPPINGS[key] = url

    return URL_MAPPINGS

def plot_agencies_stations(df, output_path=None, debug=False):
    """
    Create and optionally save a global map figure plotting stations for agencies
    where events, picks, and arrivals are all True, colored by agency.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame containing agency info with columns 'agency', 'station', 'event',
        'picks', 'arrivals'.
    output_path : str or None, optional
        File path to save the PNG figure. If None, figure is not saved.
    debug : bool, optional
        If True, print debug messages. Default is False.

    Returns
    -------
    matplotlib.figure.Figure
        The created matplotlib figure with plotted stations.
    """
    import cartopy.crs as ccrs
    import cartopy.feature as cfeature

    # Filter agencies meeting criteria
    filtered = df[
        (df["event"] == True) &
        (df["picks"] == True) &
        (df["arrivals"] == True)
    ]

    if filtered.empty:
        if debug:
            print("No agencies with events, picks, and arrivals == True.")
        return None

    fig = plt.figure(figsize=(15, 8))
    ax = plt.axes(projection=ccrs.PlateCarree())
    ax.set_global()
    ax.coastlines()
    ax.add_feature(cfeature.BORDERS, linestyle=":")
    ax.gridlines(draw_labels=True)

    # Prepare colors for each agency
    agencies = filtered["agency"].tolist()
    unique_agencies = sorted(set(agencies))
    cmap = cm.get_cmap("tab20", len(unique_agencies))
    agency_colors = {agency: cmap(i) for i, agency in enumerate(unique_agencies)}

    # Track handles for legend
    legend_handles = {}

    station_count = 0

    for _, row in filtered.iterrows():
        agency = row["agency"]
        has_station_service = row.get("station", False)

        if debug:
            print(f"Fetching stations for agency '{agency}' (station service: {has_station_service})")

        try:
            if has_station_service:
                client = Client(agency)
            else:
                continue
                client = Client("IRIS")

            inventory = client.get_stations(
                starttime=UTCDateTime(row["starttime"]),
                endtime=UTCDateTime(row["endtime"]),
                level="station"
            )

            color = agency_colors[agency]

            for network in inventory:
                for station in network.stations:
                    lat = station.latitude
                    lon = station.longitude
                    h = ax.plot(
                        lon, lat, "o", markersize=3, alpha=0.7,
                        transform=ccrs.PlateCarree(),
                        color=color,
                        label=agency if agency not in legend_handles else None
                    )
                    if agency not in legend_handles:
                        legend_handles[agency] = h[0]
                    station_count += 1

            if debug:
                print(f"\tPlotted {len(inventory.networks)} networks for {agency}")

        except Exception as e:
            if debug:
                print(f"\tFailed to fetch stations for {agency}: {e}")
            continue

    if station_count == 0 and debug:
        print("No stations plotted.")

    # Plot legend outside the axes
    ax.legend(
        handles=legend_handles.values(),
        loc='center left',
        bbox_to_anchor=(1.02, 0.5),
        title="Agency",
        fontsize="small"
    )

    plt.tight_layout()

    if output_path:
        fig.savefig(output_path, dpi=300, bbox_inches="tight")
        if debug:
            print(f"Saved plot to {output_path}")

    return fig

def catalog_generator(
                        client: FDSNClient,
                        starttime,
                        endtime,
                        chunk_seconds: int = 86400,
                        patience: int = 10,
                        **event_kwargs
                    ):
    """
    Yield event Catalogs in time chunks from a FDSN client, up to a maximum
    number of iterations (patience).

    Parameters
    ----------
    client : obspy.clients.fdsn.Client
        The FDSN client to query.
    starttime : str or UTCDateTime
        Start of the time range.
    endtime : str or UTCDateTime
        End of the time range.
    chunk_seconds : int, optional
        Time chunk size in seconds (default: 86400 = 1 day).
    patience : int or None, optional
        Maximum number of chunks to yield. If None, iterate over full time range.
    **event_kwargs : dict
        Additional keyword arguments passed to `get_events()`.

    Yields
    ------
    dict
        A dictionary containing:
        - 'catalog': obspy.core.event.Catalog object with events in the chunk.
        - 'starttime': Start time of the chunk.
        - 'endtime': End time of the chunk.
    """
    starttime = UTCDateTime(starttime)
    endtime = UTCDateTime(endtime)

    time_cursor = starttime
    iteration = 0

    while time_cursor < endtime:
        if iteration >= patience:
            logger.info(f"Patience limit of {patience} reached.")
            break

        chunk_end = min(time_cursor + chunk_seconds, endtime)

        logger.info(f"Patience [{iteration+1}/{patience}] Fetching events from {time_cursor} to {chunk_end}...")

        try:
            catalog = client.get_events(
                starttime=time_cursor,
                endtime=chunk_end,
                orderby="time-asc",
                **event_kwargs
            )
            # Restarting patience counter to -1 because we successfully fetched events
            # it is -1 because we will increment it at the end of the loop
            iteration = -1
            logger.info(f"Restarting patience iterator to 1 after successful fetch.") # 0 for the programmer but 1 for the user
        except Exception as e:
            logger.error(f"Error fetching events from {time_cursor} to {chunk_end}: {e}")
            catalog = Catalog()

        yield {"catalog": catalog, "starttime": time_cursor, "endtime": chunk_end}

        time_cursor = chunk_end
        iteration += 1

def get_valid_event_ids(catalog, tests=None):
    """
    Get a list of valid custom event IDs from a catalog using specified tests.

    Parameters:
    - catalog: list of Event objects
    - tests: dictionary of test functions to apply (optional).

    Returns:
    - ev_ids: list of valid event IDs
    - final_tests: the reduced dictionary of tests that passed
    """
    # Initialize an empty list to collect valid custom event IDs
    ev_ids = []

    # Iterate through each event in the catalog
    for event in catalog:
        # Initialize the event ID tester with the given tests
        eit = EventIDTester(event, tests=tests)

        # Iterate through all test functions
        for test_key, test_f in eit.tests.items():
            # Generate the custom event ID using the test
            ev_id = eit.get_event_id(test_key)

            # If a valid ID is returned, save it and break the loop
            if ev_id is not None:
                ev_ids.append(ev_id)

                # Update tests to only retain the successful one for consistency
                tests = {test_key: test_f}
                break
    return ev_ids, tests

class EventIDTester:
    """
    A class to test and extract event identifiers using different functions.
    """

    def __init__(self, event, tests=None):
        """
        Initialize the EventIDTester with an event object and optional test functions.

        Parameters:
        - event: An event object containing metadata.
        - tests: A dictionary of test functions (optional).
        """
        self.event = event

        if tests is None:
            tests = self._get_default_tests()
        self.tests = tests

    def _get_default_tests(self):
        """
        Define a default dictionary of test functions to extract event IDs.

        Returns:
        - dict: A dictionary where keys are test names and values are lambda functions.
        """
        tests = {
            "f1": lambda event: event.extra.datasource.value + event.extra.eventid.value,
            "f2": lambda event: event.extra.eventid.value,
            "f3": lambda event: event.extra.datasource.value,
            "f4": lambda event: event.resource_id.id.split("/")[-1],
            "f5": lambda event: event.creation_info.agency_id + event.resource_id.id.split("/")[-1]
        }
        return tests

    def get_event_id(self, function_name):
        """
        Apply the selected test function to the event and return the extracted ID.

        Parameters:
        - function_name: The key corresponding to the desired test function.

        Returns:
        - str or None: The extracted event ID or None if the function fails.
        """
        try:
            return self.tests[function_name](self.event)
        except Exception:
            return None
  