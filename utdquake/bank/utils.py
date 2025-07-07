# /**
#  * @author Emmanuel Castillo
#  * @email [castillo.280997@gmail.com]
#  * @create date 2025-05-24 14:31:48
#  * @modify date 2025-05-24 14:31:48
#  * @desc [description]
#  */
import os
import obsplus
import warnings
import sqlite3
import pandas as pd
from obspy.clients.fdsn import Client as FDSNClient 
from obspy import UTCDateTime
from obspy import UTCDateTime, Catalog
from typing import  Optional
from obspy.clients.fdsn.header import URL_MAPPINGS
import matplotlib.pyplot as plt
import matplotlib.cm as cm
from obspy.geodetics import gps2dist_azimuth, kilometer2degrees

warnings.filterwarnings("ignore", category=UserWarning, module="obspy.io.quakeml.core")

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
        raise FileNotFoundError(f"Database file not found: {db_path}")

    try:
        with sqlite3.connect(db_path) as conn:
            df = pd.read_sql("SELECT * FROM '/stations/index'", conn)
    except Exception as e:
        raise RuntimeError(f"Failed to load stations from database: {e}")

    return df

def append_stations_to_catalog(catalog: Catalog, df_stations, debug=False) -> Catalog:
    """
    Append inventory station metadata (lat/lon) to event arrivals in the catalog.
    
    Parameters:
    -----------
    catalog : obspy.core.event.Catalog
        Catalog object containing events and arrivals.
    df_stations : pandas.DataFrame
        DataFrame containing station metadata with columns:
        ['network', 'station', 'latitude', 'longitude'].
    debug : bool, optional
        If True, print debug information for each event and station processed.

    Returns:
    --------
    catalog : obspy.core.event.Catalog
        Modified catalog with arrival distances and azimuths filled (only for preferred origin).
    bad_inv_data_df : pandas.DataFrame
        DataFrame containing information about stations with missing or invalid metadata.
    """

    origin_gaps = []
    bad_inv_data = []

    # Iterate through each event in the catalog
    for event in catalog.events:
        # Iterate through each origin associated with the event
        origin = event.preferred_origin() or event.origins[0] if event.origins else None

        if debug:
            print(f"Processing event {event.resource_id.id} with origin {origin.resource_id.id}")

        olon = origin.longitude
        olat = origin.latitude

        # Track unique back-azimuths
        bazs = set()

        # Iterate through all arrivals (picks) for this origin
        for arrival in origin.arrivals:
            pick = arrival.pick_id.get_referred_object()

            # Retrieve station metadata
            network = pick.waveform_id.network_code
            station = pick.waveform_id.station_code

            _df_sta = df_stations[
                (df_stations.network == network) &
                (df_stations.station == station)
            ][['station', 'network', 'latitude', 'longitude']]

            if debug:
                print(f"Processing network: {network}, station: {station}")

            # Handle case where station metadata is missing
            if _df_sta.empty:
                bad_inv_data.append({
                    "network": network,
                    "station": station,
                    "event_id": event.resource_id.id,
                    "error": "No station data found"
                })
                if debug:
                    print(f"\tNo station data found for {network}.{station} in event {event.resource_id.id}")
                continue

            # Safely extract station latitude and longitude
            try:
                slon = _df_sta.longitude.values[0]
                slat = _df_sta.latitude.values[0]
            except Exception:
                bad_inv_data.append({
                    "network": network,
                    "station": station,
                    "event_id": event.resource_id.id,
                    "error": "Invalid station lat/lon data"
                })
                if debug:
                    print(f"\tInvalid station lat/lon data for {network}.{station} in event {event.resource_id.id}")
                continue

            # Compute distance and azimuths between origin and station
            dist_m, seaz, esaz = gps2dist_azimuth(slat, slon, olat, olon)

            # Convert distance to degrees and assign to arrival
            arrival.distance = kilometer2degrees(dist_m * 1e-3)

            # Assign event-to-station azimuth (back-azimuth)
            arrival.azimuth = esaz

    # Collect missing/invalid station data into a DataFrame
    bad_inv_data_df = pd.DataFrame(bad_inv_data)

    # Warn user if any station data was missing
    if not bad_inv_data_df.empty and debug:
        warnings.warn("Some stations had no data. Check bad_inv_data", UserWarning)

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

def generate_agency_availability_report(
    starttime: UTCDateTime,
    endtime: UTCDateTime,
    chunk_seconds: int = 3600,
    patience: int = 10,
    debug: bool = False,
    output: Optional[str] = None,
    additional_mappings: Optional[dict] = None,
    ):
    """
    Generate a report of FDSN agency capabilities, including picks and arrivals.

    Parameters
    ----------
    starttime : UTCDateTime
        Start time of the query window.
    endtime : UTCDateTime
        End time of the query window.
    chunk_seconds : int, optional
        Duration of each time chunk (in seconds). Default is 3600.
    patience : int, optional
        Number of chunks to try before giving up. Default is 10.
    debug : bool, optional
        If True, print progress and debug messages. Default is False.
    output : str or None, optional
        Path to output CSV file. If None, result is returned but not saved.
    additional_mappings : dict or None, optional
        Additional FDSN URL mappings to use.

    Returns
    -------
    pd.DataFrame
        DataFrame containing agency capabilities and pick information.
    """
    agency_info_template = {
        "agency": None,
        "starttime": starttime,
        "endtime": endtime,
        "url": None,
        "dataselect": False,
        "station": False,
        "event": False,
        "picks": False,
        "arrivals": False,
        "picks_method_name": None,
        "picks_method_mode": None,
    }

    # Merge additional mappings if provided
    url_mappings = extend_fdsn_url_mappings(additional_mappings or {}).copy()

    info = []

    for key in sorted(url_mappings.keys()):
        agency_info = agency_info_template.copy()
        agency_info["agency"] = key
        agency_info["url"] = url_mappings[key]

        if debug:
            print(f"{key:<11} {agency_info['url']}")

        try:
            client = Client(key)
        except Exception as e:
            if debug:
                print(f"\tError creating client for {key}: {e}")
            continue

        # Check which FDSN services are supported
        services = list(client.services.keys())
        for service in services:
            if service in agency_info:
                agency_info[service] = True

        # Try to retrieve picks and arrivals
        try:
            picks_service = client.picks_service(
                starttime=starttime,
                endtime=endtime,
                chunk_seconds=chunk_seconds,
                patience=patience,
            )

            agency_info["picks"] = picks_service["picks"]
            agency_info["arrivals"] = picks_service["arrivals"]
            agency_info["picks_method_name"] = picks_service["name"]
            agency_info["picks_method_mode"] = picks_service["mode"]

        except Exception as e:
            if debug:
                print(f"\tError getting picks service for {key}: {e}")

        if debug:
            print("\t", agency_info)

        info.append(agency_info)

    df = pd.DataFrame(info)

    if output:
        df.to_csv(output, index=False)
        if debug:
            print(f"\nSaved output to {output}")

    return df

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
                        debug: bool = False,
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
    debug : bool, optional
        If True, print warnings and chunk info.
    **event_kwargs : dict
        Additional keyword arguments passed to `get_events()`.

    Yields
    ------
    obspy.Catalog
        A Catalog object with events in the given time chunk.
    """
    starttime = UTCDateTime(starttime)
    endtime = UTCDateTime(endtime)

    time_cursor = starttime
    iteration = 0

    while time_cursor < endtime:
        if iteration >= patience:
            if debug:
                print(f"[Info] Patience limit of {patience} reached.")
            break

        chunk_end = min(time_cursor + chunk_seconds, endtime)

        if debug:
            print(f"Fetching events from {time_cursor} to {chunk_end}...")

        try:
            catalog = client.get_events(
                starttime=time_cursor,
                endtime=chunk_end,
                orderby="time-asc",
                **event_kwargs
            )
        except Exception as e:
            if debug:
                print(f"[Warning] Error fetching events from {time_cursor} to {chunk_end}: {e}")
            catalog = Catalog()

        yield catalog

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
  