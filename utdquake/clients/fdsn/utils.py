import os 
import re
import pandas as pd
from obspy import read_inventory
from utdquake.core.database.database import save_to_sqlite

def get_custom_picks(event):
    """
    Extract custom picks information from an event.

    Parameters:
    event : Event object
        Seismic event from which to extract pick data.

    Returns:
    dict
        Dictionary with picks information, including network, station, and 
        phase details.
    """
    picks = {}
    # Loop through each pick in the event
    for pick in event.picks:
        picks[pick.resource_id.id] = {
            ("event","pick","network_code"): pick.waveform_id.network_code if pick.waveform_id is not None else None,
            ("event","pick","station_code"): pick.waveform_id.station_code if pick.waveform_id is not None else None,
            ("event","pick","location_code"): pick.waveform_id.location_code if pick.waveform_id is not None else None,
            ("event","pick","channel_code"): pick.waveform_id.channel_code if pick.waveform_id is not None else None,
            ("event","pick","phase_hint"): pick.phase_hint,
            ("event","pick","time"): pick.time.datetime.strftime("%Y-%m-%d %H:%M:%S.%f"),
            ("event","pick","time_errors_lower_uncertainty"): pick.time_errors.lower_uncertainty if pick.time_errors is not None else None,
            ("event","pick","time_errors_upper_uncertainty"): pick.time_errors.upper_uncertainty if pick.time_errors is not None else None,
            ("event","pick","creation_info_author"): pick.creation_info.author if pick.creation_info is not None else None,
            ("event","pick","filter_id"): pick.filter_id.id if pick.filter_id is not None else None ,
            ("event","pick","method_id"): pick.method_id.id if pick.method_id is not None else None,
            ("event","pick","polarity"): pick.polarity[0] if pick.polarity is not None else None,
            ("event","pick","evaluation_mode"): pick.evaluation_mode,
            ("event","pick","evaluation_status"): pick.evaluation_status
        }
    
    return picks

def get_custom_station_magnitudes(event):
    """
    Extract custom station magnitude information from an event.

    Parameters:
    event : Event object
        Seismic event from which to extract station magnitude data.

    Returns:
    dict
        Dictionary containing station magnitudes, including network and station details.
    """
    sta_mags = {}
    
    # Loop through each station magnitude in the event
    for sta_mag in event.station_magnitudes:
        sta_mags[sta_mag.resource_id.id] = {
            ("event","station_magnitude","network_code"): sta_mag.waveform_id.network_code if sta_mag.waveform_id is not None else None,
            ("event","station_magnitude","station_code"): sta_mag.waveform_id.station_code if sta_mag.waveform_id is not None else None,
            ("event","station_magnitude","location_code"): sta_mag.waveform_id.location_code if sta_mag.waveform_id is not None else None,
            ("event","station_magnitude","channel_code"): sta_mag.waveform_id.channel_code if sta_mag.waveform_id is not None else None,
            ("event","station_magnitude","magnitude"): sta_mag.mag,
            ("event","station_magnitude","magnitude_type"): sta_mag.station_magnitude_type
        }
    
    return sta_mags

def get_custom_arrivals(ev_id, event):
    """
    Extract custom arrival information from an event and associate it with picks.

    Parameters:
    ev_id: str
        Event identificator.
    event : Event object
        Seismic event from which to extract arrival and pick data.

    Returns:
    tuple
        A tuple containing origin quality information and a DataFrame of 
        arrival contributions with associated picks.
    """
    
    origin = event.preferred_origin()
    
    # Get origin quality information
    # info = dict(origin.quality)
    
    info = {
            ("event","origin","quality_associated_phase_count"):origin.quality.associated_phase_count if origin.quality is not None else None,
            ("event","origin","quality_used_phase_count"):origin.quality.used_phase_count if origin.quality is not None else None,
            ("event","origin","quality_associated_station_count"):origin.quality.associated_station_count if origin.quality is not None else None,
            ("event","origin","quality_used_station_count"):origin.quality.used_station_count if origin.quality is not None else None,
            ("event","origin","quality_standard_error"):origin.quality.standard_error if origin.quality is not None else None,
            ("event","origin","quality_azimuthal_gap"):origin.quality.azimuthal_gap if origin.quality is not None else None,
            ("event","origin","quality_minimum_distance"):origin.quality.minimum_distance if origin.quality is not None else None,
            ("event","origin","quality_maximum_distance"):origin.quality.maximum_distance if origin.quality is not None else None,
            ("event","origin","quality_median_distance"):origin.quality.median_distance if origin.quality is not None else None,
            }
    
    # Retrieve custom picks
    picks = get_custom_picks(event)
    
    arr_contributions = {}
    
    # Loop through each arrival in the origin
    for arrival in origin.arrivals:
        
        try:
            pick_info = picks[arrival.pick_id.id]
        except Exception as e:
            print(f"Event: {ev_id} | Pick not found:",e)
            continue
        
        
        pick_info[("event","origin","arrival","time_correction")] = arrival.time_correction
        pick_info[("event","origin","arrival","azimuth")] = arrival.azimuth
        pick_info[("event","origin","arrival","distance")] = arrival.distance
        pick_info[("event","origin","arrival","takeoff_angle")] = arrival.takeoff_angle
        pick_info[("event","origin","arrival","time_residual")] = arrival.time_residual
        pick_info[("event","origin","arrival","time_weight")] = arrival.time_weight
        pick_info[("event","origin","arrival","used")] = True
        
        arr_contributions[arrival.pick_id.id] = pick_info
    
    # Identify picks not used in arrivals
    not_used_ids = list(set(picks.keys()) - set(arr_contributions.keys()))
    
    for not_used_id in not_used_ids:
        pick_info = picks[not_used_id]
        pick_info[("event","origin","arrival","time_correction")] = None
        pick_info[("event","origin","arrival","azimuth")] = None
        pick_info[("event","origin","arrival","distance")] = None
        pick_info[("event","origin","arrival","takeoff_angle")] = None
        pick_info[("event","origin","arrival","time_residual")] = None
        pick_info[("event","origin","arrival","time_weight")] = None
        pick_info[("event","origin","arrival","used")] = False
        arr_contributions[not_used_id] = pick_info
    
    # Convert contributions to a DataFrame and drop duplicates
    arr_contributions = pd.DataFrame(list(arr_contributions.values()))
    arr_contributions = arr_contributions.drop_duplicates(ignore_index=True)
    arr_contributions.insert(0, ("event","event_id"), ev_id)
    
    return info, arr_contributions

def get_custom_pref_mag(ev_id, event):
    """
    Extract custom preferred magnitude information from an event.

    Parameters:
    ev_id: str
        Event identificator.
    event : Event object
        Seismic event from which to extract preferred magnitude data.

    Returns:
    tuple
        A tuple containing preferred magnitude information and a DataFrame of 
        station magnitude contributions.
    """
    magnitude = event.preferred_magnitude()
    
    # Get preferred magnitude information
    info = {
        ("event","magnitude","magnitude"): magnitude.mag,
        ("event","magnitude","magnitude_uncertainty"): magnitude.mag_errors.uncertainty if magnitude.mag_errors is not None else None,
        ("event","magnitude","magnitude_type"): magnitude.magnitude_type,
        ("event","magnitude","magnitude_method_id"): magnitude.method_id.id.split("/")[-1] if magnitude.method_id is not None else None,
        ("event","magnitude","magnitude_station_count"): magnitude.station_count,
        ("event","magnitude","magnitude_evaluation_status"): magnitude.evaluation_status,
    }
    
    # Retrieve station magnitudes
    sta_mags = get_custom_station_magnitudes(event)
    
    mag_contributions = {}
    
    # Loop through each station magnitude contribution
    for used_sta_mag in magnitude.station_magnitude_contributions:
        
        try:
            sta_info = sta_mags[used_sta_mag.station_magnitude_id.id]
        except Exception as e:
            print(f"Event: {ev_id} | StationMagnitude not found:",e)
            continue
            
        mag_contributions[("event","magnitude","station_magnitude_contribution","residual")] = used_sta_mag.residual
        mag_contributions[("event","magnitude","station_magnitude_contribution","weight")] = used_sta_mag.weight
        mag_contributions[("event","magnitude","station_magnitude_contribution","used")] = True
        # mag_contributions[used_sta_mag.station_magnitude_id.id] = sta_info
    
    # # Identify station magnitudes not used in contributions
    # not_used_ids = list(set(sta_mags.keys()) - set(mag_contributions.keys()))
    
    # for not_used_id in not_used_ids:
    #     sta_info = sta_mags[not_used_id]
    #     sta_info["residual"] = None
    #     sta_info["weight"] = None
    #     sta_info["used"] = False
    #     mag_contributions[not_used_id] = sta_info
    
    # Convert contributions to a DataFrame and drop duplicates
    mag_contributions = pd.DataFrame(list(mag_contributions.values()))
    mag_contributions = mag_contributions.drop_duplicates(ignore_index=True)
    mag_contributions.insert(0, ("event","event_id"), ev_id)
    # mag_contributions.insert(0, "magnitude_id", magnitude.resource_id.id)
    
    return info, mag_contributions
    
def get_custom_origin(ev_id,event):
    """
    Extract custom origin information from a seismic event.

    Parameters:
    ev_id: str
        Event identificator.
    event : Event object
        The seismic event from which to extract origin data.

    Returns:
    dict
        A dictionary containing event and origin information with 
        multilevel column structure.
    """
    # from obsplus.events.utils import event_to_dataframe
    import obsplus
    from obsplus.events.pd import events_to_df
    
    # Get the preferred origin of the event
    try:
        origin = event.preferred_origin()
    except: 
        raise Exception(f"Event: {ev_id} | Origin not found")
    
    # Prepare event information
    ev_info = {
         "event_id": ev_id,
         "event_type": event.event_type,
         "event_type_certainty": event.event_type_certainty,
    }
    # print(event.__dict__)
    # print(origin.__dict__)
    # df = events_to_df(event)
    df = events_to_df(event)
    df.to_csv("/home/edc240000/UTDQuake/test/tools/test.csv")
    # print(df)
    print(df.info())
    # while True:
        
        
    
    exit()
    # Prepare location information
    loc_info = {
        ("origin", "agency"): origin.creation_info.agency_id if origin.creation_info is not None else None,
        ("origin", "evaluation_mode"): origin.evaluation_mode,
        ("origin", "evaluation_status"): origin.evaluation_status,
        ("origin", "time"): origin.time.datetime.strftime("%Y-%m-%d %H:%M:%S.%f") if origin.time is not None else None,
        ("origin", "longitude"): origin.longitude,
        ("origin", "longitude_error"): origin.longitude_errors.uncertainty,
        ("origin", "latitude"): origin.latitude,
        ("origin", "latitude_error"): origin.latitude_errors.uncertainty,
        ("origin", "depth"): origin.depth,
        ("origin", "depth_error"): origin.depth_errors.uncertainty if origin.depth_errors is not None else None,
        }
        
    method_id = origin.method_id
    if method_id is not None:
        loc_info[("event","origin", "location_method_id")] =  method_id.id.split("/")[-1] if method_id.id is not None else None
    else:
        loc_info[("event","origin", "location_method_id")] =  None
        
    earth_model_id = origin.earth_model_id
    if earth_model_id is not None:
        loc_info[("event","origin", "earth_model_id")] =  earth_model_id.id.split("/")[-1] if earth_model_id.id is not None else None
    else:
        loc_info[("event","origin", "earth_model_id")] =  None
    
    
    # Combine all information into a single dictionary
    info = ev_info.copy()
    info.update(loc_info)
    
    # for x, y in info.items():
    #     print(x, y)
    info = pd.DataFrame([info])
    info.columns = pd.MultiIndex.from_tuples(info.keys())
    
    return info
    
def get_custom_info(ev_id, event, drop_level=True):
    """
    Extracts custom information from a seismic event, including origin, picks, 
    and magnitude information.

    Parameters:
    ev_id: str
        Event identificator.
    event : Event object
        The seismic event from which to extract information.
    drop_level : bool, optional, default=True
        True if you want to have only one level in your dataframes.

    Returns:
    tuple
        A tuple containing:
        - DataFrame with combined origin, picks, and magnitude information.
        - Picks contributions as a dictionary.
        - Magnitude contributions as a dictionary.
    """
    
    # Retrieve custom origin information from the event
    origin_info = get_custom_origin(ev_id,event)
    print(origin_info)
    print(origin_info.info())
    exit()    
    # Retrieve picks information and contributions from the event
    picks_info, picks_contributions = get_custom_arrivals(ev_id,event)
    # print(picks_info, picks_contributions)
    
    # Retrieve magnitude information and contributions from the event
    mag_info, mag_contributions = get_custom_pref_mag(ev_id,event)
    
    # Prepare picks information with a multilevel column structure
    picks_info = {("picks", x): y for x, y in picks_info.items()}
    
    # Prepare magnitude information with a multilevel column structure
    mag_info = {("mag", x): y for x, y in mag_info.items()}
    
    
    # Update the origin information with magnitude information
    origin_info.update(mag_info)
    
    # Update the origin information with picks information
    origin_info.update(picks_info)
    
    
    # Convert the combined origin information into a Pandas DataFrame
    origin_info = pd.DataFrame([origin_info])
    # Create a MultiIndex for the columns using the dictionary keys (tuples)
    origin_info.columns = pd.MultiIndex.from_tuples(origin_info.keys())
    
    if drop_level:
        origin_info.columns = origin_info.columns.droplevel(0)
        
        # Separate 'qc_' columns and other columns
        qc_columns = [col for col in origin_info.columns if col.startswith('qc_')]
        other_columns = [col for col in origin_info.columns if not col.startswith('qc_')]

        # Reorder the columns
        origin_info = origin_info[other_columns + qc_columns]
        
        
        
    
    return origin_info, picks_contributions, mag_contributions

def get_event_ids(catalog):
    """
    Extracts the event IDs from a seismic catalog.

    Parameters:
    catalog : Catalog object
        The catalog containing seismic events.

    Returns:
    list
        A list of event IDs extracted from the catalog.
    """
    
    # Initialize an empty list to hold event IDs
    ev_ids = []
    
    # Iterate through each event in the catalog
    for event in catalog:
        
        # Extract the event ID from the preferred origin
        ev_id = match_event_id(event)
        
        # Append the event ID to the list
        ev_ids.append(ev_id)
    
    return ev_ids
        
def save_info(path, info):
    """
    Saves the seismic event information to CSV and SQLite database files.

    Parameters:
    path : str
        The folder path where the information will be saved.
    info : dict
        A dictionary containing seismic event information with keys like 
        'origin', 'picks', 'mags', etc. Each key has an associated DataFrame.
    """
    
    # Iterate through the info dictionary, handling each key-value pair
    for key, value in info.items():
        
        # If the key is 'origin', save it as a CSV file
        if key == "origin":
            info_path = os.path.join(path, f"{key}.csv")
            
            # Save the DataFrame to a CSV file, appending if the file already exists
            value.to_csv(
                info_path, 
                mode='a',  # Append mode
                header=not pd.io.common.file_exists(info_path),  # Add header only if the file doesn't exist
                index=False  # Do not write row numbers
            )
        else:
            # For other keys, save the data in a SQLite database
            info_path = os.path.join(path, f"{key}.db")
            
            # Group the DataFrame by 'ev_id' and iterate over each group
            for ev_id, df_by_evid in value.groupby("event_id").__iter__():
                save_to_sqlite(df_by_evid,
                                         info_path,ev_id)
                # with sqlite3.connect(info_path) as conn:
                #     # Save each group to a SQLite table, appending to the table if it exists
                #     df_by_evid.to_sql(
                #         ev_id, 
                #         conn, 
                #         if_exists='append',  # Append data to the table if it exists
                #         index=False  # Do not write row numbers
                #     )
                        
                # testing...        
                # try:
                
                #     with sqlite3.connect(info_path) as conn:
                #         # if "time" in list(df_by_evid.columns):
                #         #     df_by_evid['time'] = df_by_evid['time'].astype(str)
                #         # df_by_evid.fillna(value='NULL', inplace=True)
                #         # print(key,df_by_evid.info())
                #         # for i,row in df_by_evid.iterrows():
                #         #     print(i,row)
                #         # Save DataFrame to SQLite database, appending if the table exists
                #         # df_by_evid.to_sql(ev_id, conn, if_exists='append', index=False)
                #         df_by_evid.to_sql(ev_id, conn, if_exists='append', index=False)
                # except:
                #     print(ev_id)
                #     with sqlite3.connect(os.path.join(path,f"{key}.bad")) as conn:
                #         df_by_evid.to_csv(os.path.join(path,f"{key}.csv"))
                #         df_by_evid.to_sql(ev_id, conn, if_exists='append', index=False)
                #     # exit()

def get_channel_info(station):
    """
    Extracts channel information from an Station Object  and sorts the channels by start date.

    Args:
        station (Obspy Station Object): Station to extract the information

    Returns:
        DataFrame: A dataframe containing channel information sorted by start date.
    """
    channel_info = {
        "network": [],
        "station": [],
        "station_latitude": [],
        "station_longitude": [],
        "station_elevation": [],
        "station_starttime": [],
        "station_endtime": [],
        "channel": [],
        "location_code": [],
        "latitude": [],
        "longitude": [],
        "elevation": [],
        "depth": [],
        "site": [],
        "epoch": [],
        "starttime": [],
        "endtime": [],
        "equipment": [],
        "sampling_rate": [],
        "sensitivity": [],
        "frequency": [],
        "azimuth": [],
        "dip": [],
        "horizontal_components_exchange": [],
    }

    def get_start_date(channel):
        return channel.start_date

    # Sort the channels based on their start dates
    sorted_channels = sorted(station, key=get_start_date)

    epochs = {
        "HHE": 0,
        "HHN": 0,
        "HHZ": 0,
        "HNE": 0,
        "HNN": 0,
        "HNZ": 0,
    }

    for channel in sorted_channels:
        epochs[channel.code] += 1
        channel_info["station"].append(station.code)
        channel_info["station_latitude"].append(station.latitude)
        channel_info["station_longitude"].append(station.longitude)
        channel_info["station_elevation"].append(station.elevation)
        channel_info["station_starttime"].append(station.start_date)
        channel_info["station_endtime"].append(station.end_date)
        channel_info["channel"].append(channel.code)
        channel_info["location_code"].append(channel.location_code)
        channel_info["latitude"].append(channel.latitude)
        channel_info["longitude"].append(channel.longitude)
        channel_info["elevation"].append(channel.elevation)
        channel_info["depth"].append(channel.depth)
        channel_info["site"].append(station.site.name)
        channel_info["epoch"].append(epochs[channel.code])
        channel_info["starttime"].append(channel.start_date)
        channel_info["endtime"].append(channel.end_date)
        channel_info["equipment"].append(channel.sensor.type)
        channel_info["sampling_rate"].append(channel.sample_rate)
        
        instrument_type = channel.code[:2]
        if instrument_type == "HN":
            output_freq_gain = "ACC"
        else:
            output_freq_gain = "VEL"
        
        channel.response.recalculate_overall_sensitivity()
        freq,gain = channel.response._get_overall_sensitivity_and_gain(frequency=1.0,output = output_freq_gain)
        channel_info["sensitivity"].append(gain)
        channel_info["frequency"].append(freq)
        
        channel_info["azimuth"].append(channel.azimuth)
        channel_info["dip"].append(channel.dip)

        component = channel.code[-1]
        if component == "E":
            if channel.azimuth == 90:
                channel_info["horizontal_components_exchange"].append(False)
            elif channel.azimuth == 0:
                channel_info["horizontal_components_exchange"].append(True)
        elif component == "N":
            if channel.azimuth == 90:
                channel_info["horizontal_components_exchange"].append(True)
            elif channel.azimuth == 0:
                channel_info["horizontal_components_exchange"].append(False)
        else:
            channel_info["horizontal_components_exchange"].append(None)

    channel_info = pd.DataFrame.from_dict(channel_info)
    return channel_info

def get_station_info(station):
    """
    Extract station information from an ObsPy Station object.

    Args:
        station (obspy.core.inventory.station.Station): Station object to extract information from.

    Returns:
        dict: Dictionary containing station information, including:
            - "station": Station code.
            - "latitude": Latitude of the station.
            - "longitude": Longitude of the station.
            - "elevation": Elevation of the station.
            - "starttime": Start date and time of the station's operation.
            - "endtime": End date and time of the station's operation (or None if not defined).
            - "site_name": Name of the site (or None if not defined).
    """
    # Initialize a dictionary to store station information
    sta_info = {
        "station": station.code,
        "latitude": station.latitude,
        "longitude": station.longitude,
        "elevation": station.elevation,
        "starttime": station.start_date.datetime,
        "endtime": station.end_date.datetime if station.end_date is not None else None,
        "site_name": station.site.name if station.site is not None else None,
    }

    return sta_info


def get_stations_info(inv):
    """
    Extract station and network information from an ObsPy Inventory object.

    Args:
        inv (obspy.core.inventory.inventory.Inventory): Inventory object containing network and station data.

    Returns:
        pandas.DataFrame: A DataFrame containing station and network information with columns:
            - "network": Network code to which the station belongs.
            - "station": Station code.
            - "latitude": Latitude of the station.
            - "longitude": Longitude of the station.
            - "elevation": Elevation of the station.
            - "starttime": Start date and time of the station's operation.
            - "endtime": End date and time of the station's operation.
            - "site_name": Name of the site.
    """
    # Initialize a list to store station information from all networks
    station_info_list = []

    # Iterate over each network in the inventory
    for net in inv:
        # Iterate over each station in the network
        for sta in net:
            # Extract information for the current station and append to the list
            info = get_station_info(sta)
            info["network"] = net.code
            info["sta_id"] = ".".join((net.code,info["station"]))
            station_info_list.append(info)

    # Convert the list of station information dictionaries into a pandas DataFrame
    station_info_df = pd.DataFrame(station_info_list)
    
    first_cols = ['sta_id','network']
    station_info_df = station_info_df[ first_cols + \
                    [col for col in station_info_df.columns if (col not in first_cols)]]

    # Remove duplicate stations, keeping the last occurrence
    station_info_df = station_info_df.drop_duplicates(subset=["station"], keep="last")

    return station_info_df  
        