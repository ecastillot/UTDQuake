# /**
#  * @author Emmanuel Castillo
#  * @email [castillo.280997@gmail.com]
#  * @create date 2025-05-24 14:31:48
#  * @modify date 2025-05-24 14:31:48
#  * @desc [description]
#  */
import os
import glob
import datetime
import random
import string
import logging
import obsplus
import warnings
import sqlite3
import pandas as pd
import concurrent.futures as cf

from obspy.clients.fdsn import Client as FDSNClient 
import numpy as np
import glob
from obspy import UTCDateTime, Catalog
from typing import  Optional
from obspy.clients.fdsn.header import URL_MAPPINGS
import matplotlib.pyplot as plt
import matplotlib.cm as cm
from obspy.geodetics import gps2dist_azimuth, kilometer2degrees
from obspy.core.inventory import Inventory, Network, Station, Site, Channel
from obspy.core.event.event import Event
from obspy.core.event import Magnitude
from obspy.core.event import ResourceIdentifier, Catalog
from obspy.core.event.base import CreationInfo
from obspy.core.event.origin import Pick
from obspy.core.event.base import (
    QuantityError,
    WaveformStreamID,
    CreationInfo,
    Comment
)
from obspy.core.event.origin import Origin, OriginQuality, Arrival

from ..core.config import get_utdq_paths

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

event_columns = [ 'agency', 'event_id', 'origin_time', 'latitude',
               'longitude', 'depth[km]', 'magnitude']
               # optional columns
event_optional_columns = ['rms','latitude_error', 
                        'longitude_error', 'depth_error[km]']
picks_columns = ['agency','event_id','network',  'station', 'location', 'channel','phase',
            'instrument_type','pick_time']


# def upload_catalog_to_bank(catalog):
#     for catalog_dict in catalog_generator(catalog, starttime=starttime, endtime=endtime,
#                                  chunk_seconds=chunk_seconds,
#                                  patience=patience,reverse=reverse, **ev_kwargs):



def load_picks_from_manifest( picks_dir:str,
                            networks: list= None,
                             
                             ) -> pd.DataFrame:
    """
    Load picks from per-network Parquet manifests.

    Args:
        networks (Optional[List[str]]): List of network names to load. 
            If None, loads all networks in manifests/picks/.
        picks_dir (str): Directory where pick manifests are stored.
    Returns:
        pd.DataFrame: Combined picks for requested networks.
    """
    # picks_dir = os.path.join(self.bank_path, "manifests", "picks")

    if networks is None:
        pattern = os.path.join(picks_dir, "network=*.parquet")
        files = glob.glob(pattern)
    else:
        files = [os.path.join(picks_dir, f"network={net}.parquet") for net in networks]

    all_dfs = []
    for f in files:
        if os.path.exists(f):
            df = pd.read_parquet(f)
            all_dfs.append(df)
        else:
            logger.warning("Pick manifest not found: %s", f)

    if not all_dfs:
        return pd.DataFrame()

    # Optional: convert time columns to datetime
    time_cols = ['time', 'origin_time']
    df_combined = pd.concat(all_dfs, ignore_index=True)
    for col in time_cols:
        if col in df_combined.columns:
            df_combined[col] = pd.to_datetime(df_combined[col], errors='coerce')

    df_combined["travel_time"] = (df_combined["time"] - df_combined["origin_time"]).dt.total_seconds()

    return df_combined


def remove_tables(path, tables_to_remove, test=True):
    """
    Remove (drop) tables in a SQLite database only if they exist.

    Parameters:
        path (str): Path to the .db file.
        tables_to_remove (list): List of table names to drop.
        test (bool): If True, only show what would happen. If False, actually drop the tables.
    """
    conn = sqlite3.connect(path)
    cursor = conn.cursor()

    # Get existing tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = set(name for (name,) in cursor.fetchall())
    # print(f"[INFO] Existing tables: {tables}")
    logger.debug(f"Existing tables: {tables}")

    actions = []

    for table_name in tables_to_remove:
        if table_name in tables:
            actions.append(table_name)
        else:
            # print(f"Skipping: {table_name} does not exist.")
            logger.debug(f"Skipping: {table_name} does not exist.")

    if not actions:
        logger.info("Nothing to do.")
    else:
        if test:
            for table_name in actions:
                # print(f"[TEST MODE] Would drop: {table_name}")
                logger.info(f"[TEST MODE] Would drop: {table_name}")
        else:
            for table_name in actions:
                # print(f"[ACTION] Dropping: {table_name}")
                logger.info(f"Dropping table: {table_name}")
                cursor.execute(f'DROP TABLE "{table_name}";')
            conn.commit()
            logger.debug(" Drop operations committed.")

    conn.close()
    # print("[INFO] Done.")

def massive_remove_tables(folder_path, tables, test=True):

    networks = os.listdir(folder_path)
    for network in networks:
        if ".no_data" == network:
            continue

        network_path = os.path.join(folder_path, network)
        db_path = os.path.join(network_path, ".index.db")

        if not os.path.exists(db_path):
            print(f"[INFO] No .index.db found in {network_path}. Skipping.")
            continue

        print(f"[INFO] Processing {network_path}...")
        remove_tables(db_path, tables, test=test)

def dataframe_to_inventory(df: pd.DataFrame, network_code: str = "--",
                           source: str = "Generated from DataFrame") -> Inventory:
    """
    Convert a pandas DataFrame of station metadata to an ObsPy Inventory.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with columns:
        - 'station': Station code (e.g., 'ABASH2')
        - 'station name': Descriptive station name
        - 'latitude': Latitude in decimal degrees
        - 'longitude': Longitude in decimal degrees
        - 'elevation_m': Elevation in meters
        - 'starttime': Installation/start date (YYYY-MM-DD), can be NaN
        - 'endtime': Close/end date (YYYY-MM-DD), can be NaN

    network_code : str, optional
        Network code for the Inventory (default is "XX").

    source : str, optional
        Source string for the Inventory metadata (default is "Generated from DataFrame").

    Returns
    -------
    obspy.core.inventory.inventory.Inventory
        ObsPy Inventory object containing one Network with all stations.

    Example
    -------
    >>> inv = dataframe_to_inventory(df, network_code="JP")
    >>> inv.write("stations.xml", format="STATIONXML")
    """

    stations = []

    for _, row in df.iterrows():
        start_date = (
            UTCDateTime(row['starttime']) if pd.notnull(row['starttime']) else None
        )
        end_date = (
            UTCDateTime(row['endtime']) if pd.notnull(row['endtime']) else None
        )

        channel = Channel(
            code="--Z",
            location_code="--",
            latitude=row['latitude'],
            longitude=row['longitude'],
            elevation=row['elevation_m'],
            depth=0.0,               # sensor depth below surface in meters
            azimuth=0.0,             # assumed pointing North for vertical
            dip=-90.0,               # vertical component: dip -90 degrees
            # sample_rate=100.0,       # example sample rate in Hz
            start_date=start_date,
            end_date=end_date
        )

        station = Station(
            code=row['station'],
            latitude=row['latitude'],
            longitude=row['longitude'],
            elevation=row['elevation_m'],
            creation_date=start_date,
            termination_date=end_date,
            site=Site(name=row['station name']),
            channels=[channel]
        )

        stations.append(station)

    network = Network(
        code=network_code,
        stations=stations
    )

    inventory = Inventory(
        networks=[network],
        source=source
    )

    return inventory

def df2bank(picks_df, catalog_df, base_path,
            path_structure='{year}/{month}/{day}/{hour}',
            name_structure='{event_id_end}',
            calculate_d_az = False,
            stations_bank_path=None,
            reset_stations= False,
            format="quakeml"):
    """Create a Catalog object from picks and catalog dataframes.
    
    Args:
        picks_df (pandas.DataFrame): DataFrame containing pick information
        catalog_df (pandas.DataFrame): DataFrame containing catalog information
        
    Returns:
        Catalog: Obspy Catalog object
    """
    if not all(x in picks_df.columns.tolist() for x in picks_columns):
        raise ValueError(f"picks_df must contain the following columns: {picks_columns}")

    if not all(x in catalog_df.columns.tolist() for x in event_columns):
        raise ValueError(f"catalog_df must contain the following columns: {event_columns}")

    index_path = os.path.join(stations_bank_path, ".index.db")
    if reset_stations:
        if "/stations" in get_table_names(index_path):
            logger.info("Removing existing '/stations' table.")
            remove_tables(index_path, "/stations",test=False)
    else:
        logger.info("Not resetting stations bank. Using existing stations metadata if available.")

    station_analysis = {"total": set(), 
                            "confirmed": set(), 
                            "calculated": set(),}

    ebank = obsplus.EventBank(
            base_path=base_path,
            path_structure=path_structure,
            name_structure=name_structure,
            format=format
        )
    bank_path = ebank.bank_path
    con = sqlite3.connect(bank_path)

    stations = load_stations_metadata_from_bank(db_path=stations_bank_path)
    total_events = len(catalog_df)
    for i, row in catalog_df.iterrows():
        picks = picks_df[picks_df["event_id"] == row["event_id"]]
        picks = get_picks(picks)
        origin = get_origin(row, picks)
        mag = get_magnitude(value=row.magnitude
                ,mag_type="M",
                evaluation_mode = "manual",
                evaluation_status = "final",
                agency=row.agency,
                origin_id=origin.resource_id)

        ev = Event(
            resource_id=ResourceIdentifier(id=row.event_id, 
                                           prefix='event'),
            event_type="earthquake",
            event_type_certainty="known",
            picks=picks,
            amplitudes=[],
            focal_mechanisms=[],
            origins=[origin],
            magnitudes=[mag],
            station_magnitudes=[],
            creation_info=CreationInfo(
                author=row.agency,
                creation_time=UTCDateTime.now()
            )
        )
        ev.preferred_origin_id = origin.resource_id.id
        events = [ev]
    
        catalog = Catalog(
            events=events,
            resource_id=ResourceIdentifier(prefix='catalog'),
            creation_info=CreationInfo(
                author=events[0].creation_info.author if events else "Unknown",
                creation_time=UTCDateTime.now()
            )
        )

        if stations is not None:
            catalog,bad_inv_data = append_stations_to_catalog(catalog=catalog, 
                                                     df_stations=stations,
                                                     station_analysis=station_analysis,
                                                     con=con,
                                                     calculate_d_az=calculate_d_az)
        try:
            ebank.put_events(catalog)
            logger.info(f"Event {row.event_id} saved to bank [{i}/{total_events}].")
        except Exception as e:
            logger.error(f"Error saving event {row.event_id} to bank: {e}")

    return catalog

def sgc_catalog2std(sgc_path: str,max_events=5000) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Convert a raw SGC catalog CSV file to standard event and pick DataFrames.

    This function:
      1. Loads the raw SGC CSV catalog.
      2. Cleans and renames columns for consistency.
      3. Converts pick times to timezone-naive datetimes.
      4. Extracts instrument type.
      5. Creates an event DataFrame with unique event metadata.
      6. Unpivots P and S picks into a single picks DataFrame with phase type.

    Parameters
    ----------
    sgc_path : str
        Path to the SGC catalog CSV file.

    Returns
    -------
    events : pd.DataFrame
        DataFrame containing unique event information.
    picks_long : pd.DataFrame
        DataFrame containing picks in long format with `phase` and `pick_time`.

    Notes
    -----
    Uses global variables:
        - event_columns
        - event_optional_columns
        - picks_columns
    """


    # Read raw CSV
    picks = pd.read_csv(sgc_path, header=1, parse_dates=['time_event'],dtype={"location": "str"})
    picks.dropna(subset=['magnitude'],inplace=True)
    # Convert pick times, remove timezone
    picks['time_pick_p'] = pd.to_datetime(
        picks['time_pick_p'], format='mixed'
    ).dt.tz_convert(None)
    picks['time_pick_s'] = pd.to_datetime(
        picks['time_pick_s'], format='mixed'
    ).dt.tz_convert(None)

    # Ensure location is str

    # Rename columns to standard names
    picks.rename(columns={
        'id': 'event_id',
        'time_event': 'origin_time',
        'depth': 'depth[km]',
        'latitude_uncertainty': 'latitude_error',
        'longitude_uncertainty': 'longitude_error',
        'depth_uncertainty': 'depth_error[km]',
    }, inplace=True)

    # Extract instrument type from channel
    picks['instrument_type'] = picks['channel'].apply(lambda x: x[:2])

    # Extract unique events
    events = picks.drop_duplicates(subset=['event_id'],ignore_index=True)
    events = events.iloc[:max_events]  # Limit to max_events
    additional_columns = [col for col in events.columns if col in event_optional_columns]
    events = events[event_columns + additional_columns]

    # Reformat picks
    keep_cols = [col for col in picks_columns if col not in ['phase', 'pick_time']]
    picks = picks[keep_cols + ['time_pick_p', 'time_pick_s']]

    picks_long = pd.melt(
        picks,
        id_vars=keep_cols,
        value_vars=['time_pick_p', 'time_pick_s'],
        var_name='phase',
        value_name='pick_time'
    )
    picks_long['phase'] = picks_long['phase'].map({
        'time_pick_p': 'P',
        'time_pick_s': 'S'
    })
    picks_long.dropna(subset=['pick_time'], inplace=True)

    return events, picks_long

def get_magnitude(value,mag_type,
                evaluation_mode = "manual",
                evaluation_status = "final",
                method_id=ResourceIdentifier(),
                agency=None,
                origin_id=ResourceIdentifier(),
                comments=None):
    mag = Magnitude()
    mag.mag = value
    mag.magnitude_type = mag_type
    mag.origin_id = origin_id
    mag.evaluation_mode = evaluation_mode 
    mag.evaluation_status = evaluation_status
    mag.method_id = method_id
    if comments != None:
        mag.comments.append(Comment(comments))
    mag.creation_info = CreationInfo(agency_id=agency,
										agency_uri=ResourceIdentifier(id=agency),
										author=agency,
										author_uri=ResourceIdentifier(id=agency),
                                        )
    
    return mag

def get_picks(event_picks):
    """Convert event picks to Obspy Pick objects.
    
    Args:
        event_picks (pandas.DataFrame): DataFrame containing pick information
        Mandatory columns:
            - network: Network code
            - station: Station code
            - location: Location code (optional)
            - instrument_type: Instrument type (optional)
            - phase: Phase type (e.g., 'P', 'S')
            - time: Timestamp of the pick

        
    Returns:
        list: List of Obspy Pick objects
    """
    pick_list = []
    for i, row in event_picks.iterrows():

        if row.phase == "P":
            component = "Z"
        elif row.phase == "S":
            component = "N"
        else:
            component = ""

        if row.location is None:
            loc = ""
        else:
            loc = row.location
        if row.instrument_type is None:
            instrument_type = ""
        else:
            instrument_type = row.instrument_type

        channel = instrument_type + component

        str_id = ".".join((str(row.network), str(row.station), str(loc),
                           channel))
        
        # pick_id based on time 
        pick_id = f"Pick/{str_id}/" + UTCDateTime(row.pick_time).strftime("%Y%m%dT%H%M%S.%f")
                  
        pick_obj = Pick(
            resource_id=ResourceIdentifier(id=pick_id, prefix="pick"),
            time=UTCDateTime(row.pick_time),
            waveform_id=WaveformStreamID(
                network_code=row.network,
                station_code=row.station,
                location_code=loc,
                channel_code=channel,
                resource_uri=ResourceIdentifier(id=str_id),
                seed_string=str_id
            ),
            phase_hint=row.phase,
            creation_info=CreationInfo(
                author=row.agency,
                creation_time=UTCDateTime.now()
            ),
            method_id=row.agency,
        )
        pick_list.append(pick_obj)
    
    return pick_list

def picks2arrivals(picks):
    """Convert picks to arrivals.
    
    Args:
        picks (list): List of Pick objects
        
    Returns:
        list: List of Arrival objects
    """
    arrivals = []
    for pick in picks:
        arrival_id = pick.resource_id.id
        arrival_id = arrival_id.replace("Pick", "Arrival")
        arrival = Arrival(
            resource_id=ResourceIdentifier(id=arrival_id, prefix='arrival'),
            pick_id=pick.resource_id,
            phase=pick.phase_hint,
            creation_info=pick.creation_info
        )
        arrivals.append(arrival)
    return arrivals

def get_origin(catalog_info, event_picks):
    """Create an Origin object from catalog information and picks.
    
    Args:
        catalog_info (pandas.Series): Catalog information for the event
        event_picks (list): List of Pick objects
        
    Returns:
        Origin: Obspy Origin object
    """
    # print(type(UTCDateTime(catalog_info.origin_time)))
    origin = Origin(
    resource_id=ResourceIdentifier(
        id=UTCDateTime(catalog_info.origin_time).strftime("%Y%m%d.%H%M%S.%f"),
        prefix='origin'
    ),
    time=UTCDateTime(catalog_info.origin_time),
    longitude=catalog_info.longitude,
    longitude_errors=QuantityError(catalog_info["longitude_error"] if "longitude_error" in catalog_info else None),
    latitude=catalog_info.latitude,
    latitude_errors=QuantityError(catalog_info["latitude_error"] if "latitude_error" in catalog_info else None),
    depth=catalog_info["depth[km]"]*1e3,
    depth_errors=QuantityError(catalog_info["depth_error[km]"]*1e3 if "depth_error[km]" in catalog_info else None),
    # method_id=ResourceIdentifier(id="Test"),
    arrivals=picks2arrivals(event_picks),
    quality=OriginQuality(associated_phase_count=len(event_picks),
                        standard_error=catalog_info.rms if "rms" in catalog_info else None,
                            ),

    creation_info=CreationInfo(
        author=catalog_info.agency if "agency" in catalog_info else "Unknown",
        creation_time=UTCDateTime.now()
    )
    )
    return origin

def get_catalog(picks_df, catalog_df):
    """Create a Catalog object from picks and catalog dataframes.
    
    Args:
        picks_df (pandas.DataFrame): DataFrame containing pick information
        catalog_df (pandas.DataFrame): DataFrame containing catalog information
        
    Returns:
        Catalog: Obspy Catalog object
    """
    events = []
    for i, row in catalog_df.iterrows():
        picks = picks_df[picks_df["event_id"] == row["event_id"]]
        picks = get_picks(picks)
        origin = get_origin(row, picks)
        mag = get_magnitude(value=row.magnitude
                ,mag_type="M",
                evaluation_mode = "manual",
                evaluation_status = "final",
                agency=row.agency,
                origin_id=origin.resource_id)
        


        ev = Event(
            resource_id=ResourceIdentifier(id=row.event_id, 
                                           prefix='event'),
            event_type="earthquake",
            event_type_certainty="known",
            picks=picks,
            amplitudes=[],
            focal_mechanisms=[],
            origins=[origin],
            magnitudes=[mag],
            station_magnitudes=[],
            creation_info=CreationInfo(
                author=row.agency,
                creation_time=UTCDateTime.now()
            )
        )
        ev.preferred_origin_id = origin.resource_id.id
        events.append(ev)
    
    catalog = Catalog(
        events=events,
        resource_id=ResourceIdentifier(prefix='catalog'),
        creation_info=CreationInfo(
            author=events[0].creation_info.author if events else "Unknown",
            creation_time=UTCDateTime.now()
        )
    )
    return catalog

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

def get_preferred_origins(catalog):
    """
    Convert an ObsPy Catalog into a DataFrame and attach each event's
    preferred origin ID.

    Parameters
    ----------
    catalog : obspy.core.event.Catalog
        Catalog containing events and their metadata.

    Returns
    -------
    pandas.DataFrame
        DataFrame with event-level metadata plus a new column
        'preferred_origin_id' indicating the resource ID of each
        event's preferred origin.
    """

    events = catalog.to_df()
    preferred_origins = {}
    for event in catalog:
        # Event ID
        event_id = str(event.resource_id)

        # Preferred origin (may be None)
        origin = event.preferred_origin() or (event.origins[0] if event.origins else None)

        if origin is None:
            origin_id = None
        else:
            origin_id = str(origin.resource_id)

        preferred_origins[event_id] = origin_id

    #append origin metadata
    events['preferred_origin_id'] = events['event_id'].map(preferred_origins)

    return events

def get_nth_arrival_time(arrivals_df, n, column='time'):
    """
    Returns a Series with the Nth arrival time per event.
    If an event has fewer than N arrivals, the last arrival time is returned.

    Parameters
    ----------
    arrivals_df : pd.DataFrame
        Must contain ['event_id', 'time'].
    n : int
        Which arrival to extract (1-based indexing).

    Returns
    -------
    pd.Series
        Indexed by event_id, values are datetime64 arrival times.
    """

    # Ensure arrivals are sorted in time order
    arr_sorted = arrivals_df.sort_values(["event_id", column])

    def extract_nth(times):
        if len(times) >= n:
            return times.iloc[n-1]   # Nth arrival
        else:
            return times.iloc[-1]    # last arrival

    # Group by event and extract
    return arr_sorted.groupby("event_id")[column].apply(extract_nth)

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
    # print(merged.info())
    # exit()
    #print duplicates by station and phase
    # for x in merged.groupby(['network','station','phase']):
    #     print(x)
    
    merged.reset_index(drop=True, inplace=True)
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

    if stations is None or stations.empty:
        analysis = {
            "events": {"total": total_events},
            "arrivals": {
                "total": total_arrivals,
                "available": np.nan,  # all arrivals are considered available if no stations
                "unavailable": np.nan},
            "p_arrivals": {
                "total": total_p_arrivals,
                "available": np.nan,  # all arrivals are considered nan
                "unavailable": np.nan},
            "s_arrivals": {
                "total": total_s_arrivals,
                "available": np.nan,  # all arrivals are considered nan
                "unavailable": np.nan},
            "stations": {"total": 0, "available": 0, "unavailable": 0},
             }
        return analysis_to_df(analysis) if to_df else analysis

    stations = stations.drop_duplicates(subset=['network', 'station'],
                                            ignore_index=True)
    arrivals_with_stations = arrivals.merge(
                                            stations[['network', 'station','latitude', 
                                                    'longitude','elevation']],
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
    logger.info(f"Total arrivals: {total_arrivals} -- Available arrivals: {total_gd_arrivals} -- Unavailable arrivals: {total_bad_arrivals}")
    logger.info(f"P arrivals: {total_p_arrivals} -- Available P arrivals: {total_p_gd_arrivals} -- Unavailable P arrivals: {total_bad_p_arrivals}")
    logger.info(f"S arrivals: {total_s_arrivals} -- Available S arrivals: {total_s_gd_arrivals} -- Unavailable S arrivals: {total_bad_s_arrivals}")

    stations_with_arrivals = arrivals_with_stations.drop_duplicates(subset=['network', 'station'])
    total_stations = len(stations_with_arrivals)
    bad_stations_mask = stations_with_arrivals[['latitude', 'longitude']].isna().any(axis=1)
    bad_stations = stations_with_arrivals[bad_stations_mask]
    gd_stations = stations_with_arrivals[~bad_stations_mask]
    total_bad_stations = len(bad_stations)
    total_gd_stations = len(gd_stations)

    # Summary of stations
    logger.info(f"Summary of stations for {total_events} events:")
    logger.info(f"Total stations: {total_stations} -- Available stations: {total_gd_stations} -- Unavailable stations: {total_bad_stations}")

    analysis = {}
    analysis['events'] = {"total": total_events}
    analysis['arrivals'] = {
        "total": total_arrivals,
        "available": total_gd_arrivals,
        "unavailable": total_bad_arrivals}
    analysis['p_arrivals'] = {
        "total": total_p_arrivals, 
        "available": total_p_gd_arrivals,
        "unavailable": total_bad_p_arrivals}
    analysis['s_arrivals'] = {
        "total": total_s_arrivals,
        "available": total_s_gd_arrivals,
        "unavailable": total_bad_s_arrivals}
    analysis['stations'] = {
        "total": total_stations,
        "available": total_gd_stations,
        "unavailable": total_bad_stations}

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
    This function creates the '/stations/index' table with a primary key on
    'seed_id' to ensure inserts with the same seed_id will overwrite existing rows.
    """
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS /stations/index (
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

def update_time_from_bank(ebank, starttime, endtime, max_n_events=None, reverse=False):
    """
    Update start or end time based on the last event in the event bank,
    depending on download direction.

    Returns
    -------
    new_time : UTCDateTime or None
        New starttime (forward) or endtime (reverse), or None if no download needed.
    total_events : int
        Total number of events in the bank.
    """
    archive_bank = ebank.read_index()
    # print(archive_bank)
    total_events = len(archive_bank)
    logger.info("Total events in archive bank: %d", total_events)

    if total_events == 0:
        logger.info("Event bank empty, starting from original time.")
        return (starttime if not reverse else endtime), total_events

    last_event_time = archive_bank['time'].max()
    first_event_time = archive_bank['time'].min()

    # Determine type: pandas.Timestamp or UTCDateTime
    def minus_one_sec(t):
        if isinstance(t, UTCDateTime):
            return t - 1
        else:  # assume pandas.Timestamp
            return t - datetime.timedelta(seconds=1)

    def plus_one_sec(t):
        if isinstance(t, UTCDateTime):
            return t + 1
        else:  # assume pandas.Timestamp
            return t + datetime.timedelta(seconds=1)

    if reverse:
        # In reverse mode, endtime is limited by the latest event in bank
        new_endtime = min(endtime, minus_one_sec(first_event_time))
        if new_endtime <= starttime:
            logger.info("All events in range already downloaded (reverse).")
            return None, total_events
        return new_endtime, total_events
    else:
        # Forward mode: starttime moves after last event
        new_starttime = max(starttime, plus_one_sec(last_event_time))
        if new_starttime >= endtime:
            logger.info("All events in range already downloaded (forward).")
            return None, total_events
        return new_starttime, total_events

def add_station_record(info, table, index_path):
    """
    Add a station record to the specified database table.

    Parameters:
        info (dict): Station information with keys
                     ["network", "station", "available", "confirmed", "calculated"].
        table (str): Table name in the database.
        index_path (str): Path to the SQLite database file.
        station_analysis (set): Tracker for station statuses.
    """
    with sqlite3.connect(index_path) as con:
        df_info = pd.DataFrame([info])
        df_info.to_sql(
            table, con, if_exists='append', index=False
        )
        # print(df_info)
    logger.info(
                f"Station {info['network']}.{info['station']} added to {table} "
                f"with status {info['available']}, {info['confirmed']}, {info['calculated']}"
            )
    # valid_stations = (
    #     info["network"], 
    #     info["station"],
    #     info["available"],
    #     info["confirmed"], 
    #     info["calculated"]
    # )

    # if valid_stations not in station_analysis:
    #     try:
    #         print(info)
    #         # open a fresh connection for this call
    #         with sqlite3.connect(index_path) as con:
    #             pd.DataFrame([info]).to_sql(
    #                 table, con, if_exists='append', index=False
    #             )
    #         print(station_analysis)
    #         # update tracker
    #         station_analysis.add(valid_stations)

    #         logger.info(
    #             f"Station {info['network']}.{info['station']} added to {table} "
    #             f"with status {info['available']}, {info['confirmed']}, {info['calculated']}"
    #         )
    #     except Exception as e:
    #         logger.error(
    #             f"Failed to insert station {info['network']}.{info['station']} into {table}: {e}"
    #         )
    # else:
    #     logger.debug(
    #         f"Station {info['network']}.{info['station']} already exists in {table} "
    #         f"with status {info['available']}, {info['confirmed']}, {info['calculated']}"
    #     )

# ------------------------------------------------------
def compute_distance_azimuth(olat, olon, slat, slon):
    """
    Compute great-circle distance and back azimuth between two points.

    Parameters:
        olat (float): Origin latitude.
        olon (float): Origin longitude.
        slat (float): Station latitude.
        slon (float): Station longitude.

    Returns:
        tuple: (distance in degrees, azimuth in degrees)
    """
    dist_m, _, esaz = gps2dist_azimuth(slat, slon, olat, olon)
    dist_deg = kilometer2degrees(dist_m * 1e-3)
    return dist_deg, esaz


def get_stations_summary(stations_folder,
                         creation_starttime=None,
                         creation_endtime=None,
                         drop_duplicates=True,
                         das=False):

    stations_paths = glob.glob(os.path.join(stations_folder,".**.db"), recursive=True)

    logger.info(f"Found {len(stations_paths)} station databases in {stations_folder}.")

    summaries = []
    def get_summary(db_path):
        conn = sqlite3.connect(db_path)
        str_cols = ["network", "station", "channel"]
        bool_cols = ["available", "confirmed", "calculated", "used"]
        df = pd.read_sql_query("SELECT * FROM '/stations/index'", conn,
                                parse_dates="creation_time")
        conn.close()
        for col in bool_cols:
            if col in df.columns:
                df[col] = df[col].astype(bool)
        
        for col in str_cols:
            if col in df.columns:
                df[col] = df[col].astype(str)

        if creation_starttime is not None:
            mask = pd.to_datetime(df['creation_time']) >= pd.to_datetime(creation_starttime)
            df = df.loc[mask]
        if creation_endtime is not None:
            mask = pd.to_datetime(df['creation_time']) <= pd.to_datetime(creation_endtime)
            df = df.loc[mask]
        
        if drop_duplicates:
            if das:
                df = df.drop_duplicates(subset=['network','station','channel','origin_id'], ignore_index=True)
            else:
                df = df.drop_duplicates(subset=['network','station','origin_id'], ignore_index=True)

        if df.empty:
            return None

        # --- Collapse into one row ---
        summary = {}
        exclude_cols = {"dist_deg", "esaz", "used", "origin_id", "creation_time"}
        for col in df.columns:
            if col in exclude_cols:
                continue
            if pd.api.types.is_float_dtype(df[col]):
                summary[col] = df[col].mean()
            elif pd.api.types.is_bool_dtype(df[col]):
                summary[col] = df[col].any()   # True if any True
            elif pd.api.types.is_integer_dtype(df[col]):
                summary[col] = df[col].max()   # or sum if counts make sense
            elif col in ["network", "station", "channel"]:
                summary[col] = ",".join(df[col].unique())  # all unique values
            else:
                summary[col] = df[col].iloc[0]  # fallback

        summary["db_path"] = db_path
        summary["creation_time"] = UTCDateTime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
        return summary
    
    # for db_path in stations_paths:
    #     s = get_summary(db_path)
    #     if s is not None:
    #         summaries.append(s)

    with cf.ThreadPoolExecutor(max_workers=None) as executor:
        results = executor.map(get_summary, stations_paths)

    summaries = [r for r in results if r is not None]

    return pd.DataFrame(summaries)

# ------------------------------------------------------
def process_arrival(arrival, source_loc,
                    origin_id, 
                    df_stations,
                    ebank_index_path,
                    # table="/stations/index",
                    calculate_d_az = False,
                    das=False
                    ):
    """
    Process an individual arrival: verify pick and station information,
    optionally update distance and azimuth, and add missing or confirmed
    station records to the database.

    Parameters:
        arrival (Arrival): The arrival object to process.
        source_loc (tuple): Tuple of (latitude, longitude) for the event origin.
        station_analysis (set): Set to track station statuses.
        calculate_d_az (bool, optional): If True, compute and update distance
            and azimuth for the arrival. Default is False.

    Returns:
        dict: Dictionary with keys:
            - 'available' (bool): True if pick exists, False if not.
            - 'station' (bool): True if station is known, False if missing.
            - 'station_id' (tuple or None): (network, station) tuple if known.
            - 'dist_deg' (float or None): Computed distance in degrees, if calculated.
            - 'esaz' (float or None): Computed azimuth, if calculated.
            - 'used' (bool): True if arrival is used based on time_weight.
    """
    
    info = {"available":False,
            "network": None,
            "network_type": None,
            "station": None,
            "channel": None,
            "dist_deg": np.NaN,
            "esaz": np.NaN,
            "confirmed": False,
            "confirmed_latitude": np.NaN,
            "confirmed_longitude": np.NaN,
            "confirmed_elevation": np.NaN,
            "calculated": False,
            "calculated_latitude": np.NaN,
            "calculated_longitude": np.NaN,
            "used": False,
            "origin_id": origin_id,
            "creation_time": UTCDateTime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ")
            }


    pick = arrival.pick_id.get_referred_object()
    if pick is None or not hasattr(pick, 'waveform_id') or not pick.waveform_id:
        logger.warning(f"Arrival {arrival.resource_id.id} has no valid pick.")
        return info

    olat, olon = source_loc
    net = pick.waveform_id.network_code
    sta = pick.waveform_id.station_code
    cha = pick.waveform_id.channel_code
    info["network"] = net
    info["station"] = sta
    info["channel"] = cha
    phase = arrival.phase
    
    df_sta = df_stations[(df_stations.network == net) & (df_stations.station == sta)]
    
    if df_sta is None:
        pass
    elif df_sta.empty:
        logger.warning(f"Station {net}.{sta} not found in station metadata.")
        pass
    else:
        df_sta = df_sta.reset_index(drop=True)
        row = df_sta.iloc[0]
        network_type = row.get("network_type", "surface")
        info["network_type"] = network_type

        if network_type in ["DAS","das","fiber_optic"] or das:
            df_sta = df_sta[df_sta["channel"].astype(str) == str(cha)]
            if df_sta.empty:
                logger.warning(f"Station {net}.{sta}.{cha} not found in station metadata.")
                pass

        if not df_sta.empty:
            row = df_sta.iloc[0]
            # If station confirmed for first time, add to confirmed table
            info["available"] = True
            info["confirmed"] = True
            info["confirmed_latitude"] = row["latitude"]
            info["confirmed_longitude"] = row["longitude"]
            info["confirmed_elevation"] = row["elevation"]

            if calculate_d_az:
                slat, slon = df_sta[["latitude", "longitude"]].values[0]
                dist_deg, esaz = compute_distance_azimuth(olat, olon, slat, slon)

                # print(olat, olon, slat, slon)
                # print(dist_deg, esaz)
                # Update arrival with correct geometry
                arrival.distance = dist_deg
                arrival.azimuth = esaz


        info["dist_deg"] = arrival.distance 
        info["esaz"] = arrival.azimuth
            
    # check if distance and azimuth are attributes of arrival
    if hasattr(arrival, 'distance') and hasattr(arrival, 'azimuth'):
        # also check if they are not None
        if arrival.distance is not None and arrival.azimuth is not None:
            original_distance = arrival.distance
            original_azimuth = arrival.azimuth
            sta_lat, sta_lon = destination_point(olat, olon, 
                                original_azimuth, 
                                original_distance)
            info["available"] = True
            info["dist_deg"] = arrival.distance 
            info["esaz"] = arrival.azimuth
            info["calculated"] = True
            info["calculated_latitude"] = sta_lat
            info["calculated_longitude"] = sta_lon
        else:
            logger.warning(f"Arrival {arrival.resource_id.id} has no valid distance or azimuth.")

    info["used"] = arrival.time_weight is None or arrival.time_weight > 0
    
    # print("phase",phase,info)

    # only save if phase is P

    # if phase == "P":
    # stations_folder = os.path.join( os.path.dirname(ebank_index_path),".stations")

    #finding the corresponding stations folder for the network
    network_name = os.path.basename(os.path.dirname(ebank_index_path))
    utdq_paths = get_utdq_paths(network_name)
    stations_folder = utdq_paths["utdq/db/.stations"]

    # stations_folder = os.path.join( stations_folder,".stations")

    os.makedirs(stations_folder, exist_ok=True)
    if das:
        stations_db_ev_path = os.path.join(stations_folder,f".{net}_{sta}_{cha}.db")
    else:
        stations_db_ev_path = os.path.join(stations_folder,f".{net}_{sta}.db")

    logger.info(stations_db_ev_path)

    with sqlite3.connect(stations_db_ev_path) as con:
        df_info = pd.DataFrame([info])
        df_info.to_sql(
            "/stations/index", con, if_exists='append', index=False
        )

    logger.debug(
                f"Station {info['network']}.{info['station']}.{info['channel']} added to /stations/index "
                f"with status {info['available']}, {info['confirmed']}, {info['calculated']}"
            )

    return info

# ------------------------------------------------------
def update_origin_quality(origin, distances, esazs, stations_used, used_phase_count):
    """
    Update the Origin's quality metrics with calculated distances and azimuths.

    Parameters:
        origin (Origin): The origin object to update.
        distances (list of float): List of distances in degrees.
        esazs (list of float): List of azimuths in degrees.
        stations_used (set): Set of station IDs used.
        used_phase_count (int): Count of phases actually used.
    """
    quality = origin.quality
    logger.info(f"Updating quality metrics for origin {origin.resource_id.id}.")
    quality.associated_phase_count = len(origin.arrivals)
    quality.used_phase_count = used_phase_count
    quality.used_station_count = len(stations_used)

    if distances:
        quality.minimum_distance = min(distances)
        quality.maximum_distance = max(distances)
        quality.median_distance = float(np.median(distances))

    if len(esazs) >= 2:
        esazs = sorted(set(esazs))
        gaps = [esazs[i + 1] - esazs[i] for i in range(len(esazs) - 1)]
        gaps.append(360 - esazs[-1] + esazs[0])
        quality.azimuthal_gap = max(gaps)
        if len(gaps) >= 2:
            quality.secondary_azimuthal_gap = sorted(gaps)[-2]
    logger.info(f"Quality metrics updated for origin {origin.resource_id.id}.")

# ------------------------------------------------------
def parse_origin(origin, 
                ebank_index_path,
                df_stations=None,
                calculate_d_az=True,
                require_arrivals=True,
                das=False
                ):
    """
    Process all arrivals in a seismic Origin: verify picks, update
    distance and azimuth if requested, manage station records, and
    update the Origin's quality metrics.

    Parameters:
        origin (Origin): The seismic event origin object.
        df_stations (DataFrame, optional): DataFrame of known stations.
            If None, an empty DataFrame is used.
        calculate_d_az (bool, optional): If True, compute distance and
            azimuth for each arrival. Default is True.

    Returns:
        bool: True if the origin was processed successfully,
              False if skipped due to too many missing picks.
    """

    source_loc = origin.latitude, origin.longitude
    arrivals = origin.arrivals
    origin_id = origin.resource_id.id

    if require_arrivals and len(arrivals) == 0:
        logger.warning(f"Origin {origin_id} has no arrivals. Skipping.")
        return False

    distances = []
    esazs = []
    stations_used = set()
    used_phase_count = 0
    none_picks = 0

    for arrival in arrivals:
        info = process_arrival(
                        arrival=arrival, source_loc=source_loc,
                        origin_id=origin_id,
                        df_stations=df_stations,
                        calculate_d_az=calculate_d_az, 
                        ebank_index_path=ebank_index_path, 
                        das=das
                                                    )
        # print("############### INFO",info)
        if not info["available"]:
            none_picks += 1
            continue

        if info["station"] is not None:
            distances.append(info["dist_deg"]  )
            esazs.append(info["esaz"] )
            stations_used.add(info["station"])

        if info["used"]:
            used_phase_count += 1


    # If too many missing picks, skip
    if none_picks > len(arrivals) / 2:
        logger.warning("More than half of arrivals have no picks. Skipping.")
        return False
    # print("Done processing origin ",origin_id)
    logger.info(f"Processed origin {origin_id}. Ready to update quality metrics.")
    update_origin_quality(origin, distances, esazs, stations_used, used_phase_count)
    logger.info(f"Updated quality metrics for origin {origin_id}.")
    return True

def xxx(origin, df_stations, 
                station_analysis, 
                con):
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
    station_analysis : dict
        A dict of lists: {"missing": [], "confirmed": [], "calculated": []}.

    Returns
    -------
    bool
        True if the origin was processed successfully, False if more than half of arrivals had no associated picks.
    """
    olat, olon = origin.latitude, origin.longitude
    arrivals = origin.arrivals

    distances = []
    esazs = []
    stations_used = set()
    used_phase_count = 0

    logger.debug(f"Processing origin {origin.resource_id.id} with {len(arrivals)} arrivals")

    none_picks = 0
    for arrival in arrivals:

        pick = arrival.pick_id.get_referred_object()
        if pick is None:
            logger.warning(f"Arrival {arrival.resource_id} from {origin.resource_id.id} has no pick associated. Skipping.")
            none_picks += 1
            continue

        if not hasattr(pick, 'waveform_id') or not pick.waveform_id:
            logger.warning(f"Arrival {arrival.resource_id} from {origin.resource_id.id} has no waveform_id in pick. Skipping.")
            none_picks += 1
            continue
        
        net = pick.waveform_id.network_code
        sta = pick.waveform_id.station_code

        logger.debug(f"Processing arrival for {net}.{sta}")
        df_sta = df_stations[
            (df_stations.network == net) & (df_stations.station == sta)
        ]

        if df_sta.empty:
            
            if (net, sta) not in station_analysis["missing"]:
                # add missing station metadata to station_analysis["missing"]
                missing_info ={
                    "network": net,
                    "station": sta,
                    "latitude": np.NaN,
                    "longitude": np.NaN,
                    "status": "missing",
                    "creation_time": UTCDateTime.now().strftime("%Y-%m-%d %H:%M:%S.%f")}
                missing_info = pd.DataFrame([missing_info])
                missing_info.to_sql("/stations/missing",
                                    con, 
                                    if_exists='append', 
                                    index=False)
                station_analysis["missing"].add((net, sta))
                logger.info(f"station {net}.{sta}: Missing metadata in inventory for origin {origin.resource_id.id}"
                "and saving to /stations/missing table.")

            continue
        else:
            # logger.info(f"Found station metadata for {net}.{sta} in stations")
            if (net, sta) not in station_analysis["confirmed"]:
                row = df_sta.iloc[0]
                confirmed_info = {
                    "network": row["network"],
                    "station": row["station"],
                    "latitude": row["latitude"],
                    "longitude": row["longitude"],
                    "status": "confirmed",
                    "creation_time": UTCDateTime.now().strftime("%Y-%m-%d %H:%M:%S.%f")}
                confirmed_info = pd.DataFrame([confirmed_info])
                confirmed_info.to_sql("/stations/confirmed",
                                    con,
                                    if_exists='append',
                                    index=False)
                station_analysis["confirmed"].add((net, sta))

                logger.info(f"Station {net}.{sta}: Confirmed in inventory "
                "and saved to /stations/confirmed table.")


        try:
            original_distance = arrival.distance
            original_azimuth = arrival.azimuth
            

            slat, slon = df_sta[["latitude", "longitude"]].values[0]
            dist_m, _, esaz = gps2dist_azimuth(slat, slon, olat, olon)
            dist_deg = kilometer2degrees(dist_m * 1e-3)

            arrival.distance = dist_deg
            arrival.azimuth = esaz

            distances.append(dist_deg)
            esazs.append(esaz)
            stations_used.add((net, sta))

            if (net, sta) not in station_analysis["calculated"]:
                # logger.info(f"Calculating station location for {net}.{sta} ")
                # calculating station location
                sta_lat,sta_lon = destination_point(
                                        olat, olon, 
                                        original_azimuth, 
                                        original_distance)
                calculated_info = {
                    "network": net,
                    "station": sta,
                    "latitude": sta_lat,
                    "longitude": sta_lon,
                    "status": "calculated",
                    "creation_time": UTCDateTime.now().strftime("%Y-%m-%d %H:%M:%S.%f")}
                calculated_info = pd.DataFrame([calculated_info])
                calculated_info.to_sql("/stations/calculated",
                                    con,
                                    if_exists='append',
                                    index=False)
                station_analysis["calculated"].add((net, sta))
                logger.info(f"Station {net}.{sta}: Location calculated"
                " and saved to /stations/calculated table.")



            if arrival.time_weight is None or arrival.time_weight > 0:
                used_phase_count += 1
        

        except Exception as e:
            logger.error(f"Error processing {net}.{sta} in origin {origin.resource_id.id}: {e}")
            if (net, sta) not in station_analysis["missing"]:
                missing_info = {
                        "network": net,
                        "station": sta,
                        "latitude": np.NaN,
                        "longitude": np.NaN,
                        "status": "missing",
                        "creation_time": UTCDateTime.now().strftime("%Y-%m-%d %H:%M:%S.%f")}
                missing_info = pd.DataFrame([missing_info])
                missing_info.to_sql("/stations/missing",
                                        con, 
                                        if_exists='append', 
                                        index=False)
                station_analysis["missing"].add((net, sta))
                logger.info(f"station {net}.{sta}: Missing metadata in inventory for origin {origin.resource_id.id}"
                "and saving to /stations/missing table.")

    if none_picks > len(arrivals)/2:
        logger.warning(f"More than half of arrivals ({none_picks}/{len(arrivals)}) in origin {origin.resource_id.id} have no associated picks. Skipping origin.")
        
        return False

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
    
    return True

def destination_point(lat1_deg, lon1_deg, azimuth_deg, distance_deg):
    """
    spherical forward problem
    Compute destination lat/lon given a starting point, azimuth, and distance in degrees.

    Args:
        lat1_deg: Latitude of starting point (degrees)
        lon1_deg: Longitude of starting point (degrees)
        azimuth_deg: Azimuth/bearing from point (degrees clockwise from North)
        distance_deg: Angular distance (degrees of arc)

    Returns:
        (lat2_deg, lon2_deg): Tuple of destination coordinates in degrees
    """
    # Convert to radians
    lat1 = np.deg2rad(lat1_deg)
    lon1 = np.deg2rad(lon1_deg)
    az = np.deg2rad(azimuth_deg)
    d = np.deg2rad(distance_deg)

    # Spherical forward calculation
    lat2 = np.arcsin(
        np.sin(lat1) * np.cos(d) +
        np.cos(lat1) * np.sin(d) * np.cos(az)
    )

    lon2 = lon1 + np.arctan2(
        np.sin(az) * np.sin(d) * np.cos(lat1),
        np.cos(d) - np.sin(lat1) * np.sin(lat2)
    )

    # Convert back to degrees
    lat2_deg = np.rad2deg(lat2)
    lon2_deg = np.rad2deg(lon2)

    # Normalize longitude to [-180, 180]
    lon2_deg = (lon2_deg + 180) % 360 - 180

    return lat2_deg, lon2_deg

def random_string(length=8):
    """
    Generate a random alphanumeric string.

    Parameters:
        length (int): Length of the string (default 8).

    Returns:
        str: Random string.
    """
    chars = string.ascii_letters + string.digits  # a-z, A-Z, 0-9
    return ''.join(random.choices(chars, k=length))

def append_stations_to_catalog(catalog: Catalog, df_stations,
                        ebank_index_path: str, 
                        calculate_d_az=True,
                        das=False
                        ) -> tuple[Catalog, pd.DataFrame]:
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
    """
    random_id = random_string(8)
    logger.info(f"Starting to process {len(catalog.events)} events in catalog {random_id}. (This id is created just for logging purposes)")

    for event in catalog:
        origin = event.preferred_origin() or (event.origins[0] if event.origins else None)

        if origin is None:
            logger.warning(f"Event {event.resource_id.id} has no origin. Skipping.")
            continue

        logger.info(f"Processing event {event.resource_id.id} with origin {origin.resource_id.id}")
        gd_proc = parse_origin(origin=origin, 
                                ebank_index_path=ebank_index_path,
                                df_stations=df_stations,
                                calculate_d_az=calculate_d_az,
                                das=das
                                )
        if not gd_proc:
            logger.warning(f"Removing event {event.resource_id.id} due to too many missing picks.")
            # If more than half of arrivals had no associated picks, skip this event
            catalog.events.remove(event)


    logger.info(f"Finishing to process {len(catalog.events)} events in catalog {random_id}.")

    return catalog

def get_table_names(index_path):
        """
        Returns a list of table names in the event bank.
        """
        conn = sqlite3.connect(index_path)
        query = "SELECT name FROM sqlite_master WHERE type='table';"
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df['name'].tolist()

def _read_table(index_path,query):
        """
        Returns a summary of the event bank.
        """
        conn = sqlite3.connect(index_path)
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df

def get_picks_summary(index_path):
        """
        Returns a summary of the event bank.
        """
        query = "SELECT * FROM '/picks/summary'"
        df = _read_table(index_path,query)
        df["creation_time"] = pd.to_datetime(df["creation_time"], errors='coerce')
        df.set_index("index", inplace=True)
        return df



def check_existing_Events(
        index_path: str,
        catalog):
    
    events = get_event_client(catalog).get_events()
    event_ids = [str(x.resource_id) for x in events]
    df = self.read_index(event_id=event_ids).set_index("event_id")

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
        reverse: bool = False,   #new
        orderby: bool = True,  #new
        **event_kwargs
    ):
    """
    Yield event Catalogs in time chunks from a FDSN client, forward or backward
    in time, up to a maximum number of iterations (patience).
    """

    starttime = UTCDateTime(starttime)
    endtime = UTCDateTime(endtime)

    if orderby:
        if not reverse:
            event_kwargs["orderby"] = "time-asc"
        else:
            event_kwargs["orderby"] = "time"
    else:
        event_kwargs.pop("orderby", None)

    iteration = 0
    if not reverse:
        # ---------- FORWARD ----------
        time_cursor = starttime
        while time_cursor < endtime:
            if iteration >= patience:
                logger.info(f"Patience limit of {patience} reached.")
                break

            chunk_end = min(time_cursor + chunk_seconds, endtime)
            logger.info(f"[{iteration+1}/{patience}] Fetching events forward {time_cursor} to {chunk_end}...")

            try:
                
                # print(time_cursor,chunk_end,event_kwargs)
                catalog = client.get_events(
                    starttime=time_cursor,
                    endtime=chunk_end,
                    # orderby="time-asc",
                    **event_kwargs
                )
                # print("here",time_cursor,chunk_end,event_kwargs, catalog)
                iteration = -1
                logger.info("Restarting patience counter after successful fetch.")
            except Exception as e:
                logger.error(f"Error fetching events from {time_cursor} to {chunk_end}: {e}")
                catalog = Catalog()

            yield {"catalog": catalog, "starttime": time_cursor, "endtime": chunk_end}

            time_cursor = chunk_end
            iteration += 1

    else:
        # ---------- REVERSE ----------
        time_cursor = endtime
        while time_cursor > starttime:
            if iteration >= patience:
                logger.info(f"Patience limit of {patience} reached.")
                break

            chunk_start = max(starttime, time_cursor - chunk_seconds)
            logger.info(f"[{iteration+1}/{patience}] Fetching events backward {chunk_start} to {time_cursor}...")

            try:
                # print(chunk_start,time_cursor,event_kwargs)
                catalog = client.get_events(
                    starttime=chunk_start,
                    endtime=time_cursor,
                    # orderby="time",  
                    **event_kwargs
                )
                iteration = -1
                logger.info("Restarting patience counter after successful fetch.")
            except Exception as e:
                logger.error(f"Error fetching events from {chunk_start} to {time_cursor}: {e}")
                catalog = Catalog()

            yield {"catalog": catalog, "starttime": chunk_start, "endtime": time_cursor}

            time_cursor = chunk_start
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
  