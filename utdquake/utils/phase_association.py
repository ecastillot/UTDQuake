# Core packages
import random
import numpy as np
import pandas as pd

# Matplotlib
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import matplotlib.cm as cm


# ObsPy and related
import obspy
from obspy.geodetics import  gps2dist_azimuth

# SciPy
from scipy.stats import linregress


def min_window_fixed(arrivals):
    arrivals = np.array(arrivals, dtype=float)
    N = len(arrivals)

    if N == 1:
        return arrivals[0]

    last = arrivals[-1]
    deltas = []

    for i in range(N-1):
        num = arrivals[i] - last
        denom = (N - 1 - i)

        # This gives a candidate Δ
        d = num / denom
        deltas.append(d)

    delta_min = max([0] + deltas)  # Δ cannot be negative

    W_min = (N - 1) * delta_min + last
    return W_min

def fixed_spacing(arrivals, window_size):
    arrivals = np.array(arrivals, dtype=float)
    N = len(arrivals)

    if N == 1:
        return np.array([0.0])

    origins = np.linspace(0, window_size, N)

    if np.any(origins + arrivals > window_size):
        raise ValueError(
            "Window too small for fixed spacing. "
            "Minimum required window = %.3f" % min_window_fixed(arrivals)
        )

    return origins

def synthetic_wavelet(t, t0, phase):
    """
    Very small ringing at onset, then fast decay.
    P: narrow, slightly more impulsive
    S: wider, softer
    """
    if phase == "P":
        sigma = 0.9
        freq = 10          # LOW frequency = small wiggle
        ring_amp = 0.1    # SMALL oscillation amplitude
    else:
        sigma = 1.8
        freq = 7           # even softer for S
        ring_amp = 0.18

    # Gaussian envelope
    envelope = np.exp(-0.5 * ((t - t0) / sigma)**2)

    # Very small, very fast-decaying wiggle
    carrier = ring_amp * np.sin(freq * (t - t0)) * np.exp(-3 * np.abs(t - t0))

    # Impulsive part = envelope itself
    pulse = envelope

    # Combine: mostly impulsive bump + a tiny wiggle on top near t0
    return pulse + carrier

def plot_window_times(
    arrivals,
    last_allowed_arrival,
    save_path,
    relative_per_event=False,
    p_color="orange",
    s_color="green",
    last_event_id= None,
    last_p_color="blue",
    last_s_color="cyan",
    phase_column="phase",
):
    """
    Plot arrival window times vs index.

    - P and S phases colored by p_color / s_color.
    - If highlight_last_event=True:
        Last event P phases use last_p_color (default red)
        Last event S phases use last_s_color (default black)
    - Supports relative per-event y indexing.
    - Draws a vertical threshold line.
    """

    df = arrivals.copy()

    # Relative per-event y axis
    if relative_per_event:
        df["y"] = df.groupby("event_id").cumcount()
    else:
        df["y"] = df.index

    # Base color (P/S)
    df["color"] = df[phase_column].map({
        "P": p_color,
        "S": s_color
    }).fillna("gray")

    # Highlight last event if enabled
    if last_event_id is not None:
        is_last = df["event_id"] == last_event_id

        # Override colors only for the last event
        df.loc[is_last & (df[phase_column] == "P"), "color"] = last_p_color
        df.loc[is_last & (df[phase_column] == "S"), "color"] = last_s_color

    # --- Plot ---
    fig, ax = plt.subplots(figsize=(12, 7))

    ax.scatter(df["window_time"], df["y"], s=10, c=df["color"])


    # Threshold line
    ax.axvline(last_allowed_arrival, color="red", linestyle="--", linewidth=2)

    # Labels
    ax.set_xlabel("Window Time (s)")
    ax.set_ylabel("Relative Index per Event" if relative_per_event else "Index")
    ax.set_title("Arrival Window Times (Colored by Phase | Last Event Highlighted)")

    # Legend
    ax.scatter([], [], color=p_color, label="P phase")
    ax.scatter([], [], color=s_color, label="S phase")

    if last_event_id is not None:
        ax.scatter([], [], color=last_p_color, label="Last Event P")
        ax.scatter([], [], color=last_s_color, label="Last Event S")

    ax.legend(loc="upper left")


    # Save
    plt.tight_layout()
    plt.savefig(save_path, dpi=200)
    plt.close()


def seismic_impulse_peak(points, dt=0.001, freq=20, damping=5, phase='P'):
    t = np.arange(points) * dt
    
    if phase.upper() == 'P':
        gaussian = np.exp(- (t/0.002)**2 )
        decay = np.exp(-damping * t)
        f = freq * 2
    elif phase.upper() == 'S':
        gaussian = np.exp(- (t/0.01)**2 )
        decay = np.exp(-damping/3 * t)
        f = freq
    else:
        raise ValueError("phase must be 'P' or 'S'")

    wave = gaussian + np.sin(2*np.pi*f*t) * decay
    return wave

def create_seismic_trace(
        total_points=2000,
        wave_length=120,
        positions=None,
        colors=None,
        pad=20,
        dt=0.001,
        freq=30,
        damping=20,
        phase='P'
    ):
    """
    Create a synthetic seismic trace and return all components needed for plotting.

    Returns a dictionary:
        {
            "seismo": 1D array,
            "waves": list of (padded_start, padded_end, wave, pos, end, color)
        }
    """
    if positions is None:
        positions = [200, 600, 1200, 1700]
    if colors is None:
        colors = ['r', 'g', 'b', 'orange']

    seismo = np.zeros(total_points)
    waves = []

    for i, pos in enumerate(positions):

        # generate impulse
        wave = seismic_impulse_peak(
            wave_length, dt=dt, freq=freq, damping=damping, phase=phase
        )

        # insert wave
        end = min(pos + wave_length, total_points)
        seismo[pos:end] += wave[:end - pos]

        # padding region for coloring
        padded_start = max(0, pos - pad)
        padded_end = min(total_points, end + pad)

        # save info
        waves.append((padded_start, padded_end, wave, pos, end, colors[i]))

    return {
        "seismo": seismo,
        "waves": waves,
    }

def plot_seismic_stations(
        df,
        save_path,
        total_points=2000,
        wave_length=120,
        sr=100,        # NEW PARAMETER
        freq=30,
        damping=100,
        top_n=None,
        color_by_event=True
    ):
    
    dt = 1.0 / sr   # sampling interval in seconds
    
    df = df.drop_duplicates(subset=["station", "event_id", "phase"])

    if top_n is not None:
        station_counts = df["station"].value_counts()
        top_stations = station_counts.head(top_n).index
        df = df[df["station"].isin(top_stations)]

    stations = df["station"].unique()
    stations = np.sort(stations)

    # If coloring by event, create color map
    if color_by_event:
        unique_events = df["event_id"].unique()
        n_events = len(unique_events)
        cmap = cm.get_cmap("tab20", min(n_events, 20))
        event_colors = {ev: cmap(i % 20) for i, ev in enumerate(unique_events)}

    fig, ax = plt.subplots(figsize=(14, 8))

    trace_scale = 1.0  # vertical scaling

    for s_i, station in enumerate(stations):

        df_s = df[df["station"] == station]

        positions = df_s["window_sample"].astype(int).values
        phases    = df_s["phase"].values
        event_ids = df_s["event_id"].values

        # Decide colors
        if color_by_event:
            colors = [event_colors[eid] for eid in event_ids]
        else:
            colors = ["#007A33" if p == "P" else "#005BBB" for p in phases]

        trace = np.zeros(total_points)
        wave_infos = []

        for pos, phase, color in zip(positions, phases, colors):

            pos = int(pos)
            if pos < 0 or pos >= total_points:
                continue

            data = create_seismic_trace(
                total_points=total_points,
                wave_length=wave_length,
                positions=[pos],
                colors=[color],
                pad=0,
                dt=dt,
                freq=freq,
                damping=damping,
                phase=phase
            )

            trace += data["seismo"]

            for item in data["waves"]:
                wave_infos.append(item)

        # X axis in seconds
        x_sec = np.arange(total_points) * dt

        # # full trace 
        # # ax.plot( # x_sec, # trace * trace_scale + s_i,
        #  # color="black", # linewidth=1 # )

        # Plot colored segments
        for padded_start, padded_end, wave, pos, end, color in wave_infos:
            x = np.arange(padded_start, padded_end) * dt
            y = np.zeros_like(x, dtype=float)

            inner_start = max(0, pos - padded_start)
            inner_end = inner_start + (end - pos)

            y[inner_start:inner_end] = wave[:inner_end - inner_start]

            ax.plot(
                x, y * trace_scale + s_i,
                color=color,
                linewidth=1.5
            )

    ax.set_yticks(range(len(stations)))
    ax.set_yticklabels([])

    ax.set_xlabel("Time (seconds)")
    ax.set_ylabel("Station")
    ax.set_title("Synthetic Seismic Signals per Station")
    ax.set_xlim(0, total_points * dt)
    ax.set_ylim(-1, len(stations))

    plt.tight_layout()
    plt.savefig(save_path, dpi=200)
    plt.close()

class EQWindow:
    def __init__(self, stations, 
                length=None,
                first_event_w=0.05, #percentage from 0 to 1 of the length
                last_event_w=0.05, #percentage from 0 to 1 of the length
                event_spacing="fixed", #fixed, random, free
                min_n_phase=5,  
                event_order="time"):

        self.length = length  # total window length in seconds
        self.first_event_w = first_event_w
        self.last_event_w = last_event_w
        self.event_spacing = event_spacing  # "fixed" or "random" or "free"
        self.min_n_phase = min_n_phase
        self.event_order = event_order  # "time" or "random" or column name

        self.event_origins = pd.DataFrame()
        self.arrivals = pd.DataFrame()

        self.stations = stations  # DataFrame with station info

        if self.first_event_w < 0 or self.last_event_w < 0 or self.first_event_w + self.last_event_w >=1:
            raise ValueError("first_event_w and last_event_w must be >=0 and their sum < 1")

        if 'latitude' not in stations.columns or 'longitude' not in stations.columns:
            raise ValueError(f"Columns 'latitude' or 'longitude' not found in stations dataframe")

    def sort_events(self,subset ="time"):
        if self.event_origins.empty:
            return

        self.event_origins.sort_values(subset, inplace=True)
        self.random_order = False

    def randomize_events(self):
        """
        Randomly shuffle the rows of the event_origins DataFrame.

        Notes
        -----
        - If `event_origins` is empty, the method returns immediately.
        - `sample(frac=1)` returns all rows in random order.
        - `reset_index(drop=True)` removes the old index and assigns a new one.
        """
        if self.event_origins.empty:
            return
        self.event_origins = self.event_origins.sample(frac=1).reset_index(drop=True)

    def _update_timeline(self):

        if self.event_origins.empty:
            return

        events = self.event_origins.copy()
        

        n_events = len(events)
        if n_events == 0:
            return

        if self.event_order == None:
            events.reset_index(drop=True, inplace=True)  # keep original order
        elif self.event_order == "random":
            events = events.sample(frac=1).reset_index(drop=True)
        else:
            try:
                events = events.sort_values(by=self.event_order).reset_index(drop=True)
            except KeyError:
                raise ValueError(f"Invalid event_order: {self.event_order}.")
        
        #add a new column with the time of the Nth arrival per event
        arrivals = self.arrivals.copy()
        min_phase = int(self.min_n_phase)
        
        nth_tt = get_nth_arrival_time(arrivals, n=min_phase,column="travel_time")
        
        nth_tt_per_ev = events["event_id"].map(nth_tt).to_numpy()

        max_nth_tt = np.nanmax(nth_tt_per_ev)
        # max_last_nth_tt = np.nanmax(last_nth_tt_per_ev)

        if self.length is not None:
            w = self.length
        else:
            w = 2*max_nth_tt
            self.length = w

        # ev_w = w - 3*w/4
        ev_w = w - self.last_event_w

        ev_w_start_pad = np.random.uniform(0,w * self.first_event_w)
        ev_w_end_pad = np.random.uniform(0,w * self.last_event_w)

        if self.event_spacing == "fixed":
            ev_times = np.linspace(ev_w_start_pad, ev_w, n_events, endpoint=True)
        elif self.event_spacing == "random":
            ev_times = np.sort(np.random.uniform(ev_w_start_pad, ev_w, n_events))
        elif self.event_spacing == "free":
            ev_times = np.array(nth_tt_per_ev)
        else:
            raise ValueError("event_spacing must be 'fixed', 'random', or 'free'")


        events["window_time"] = ev_times
        
        arrivals["origin_window_time"] = arrivals["event_id"].map(events.set_index("event_id")["window_time"])
        arrivals["window_time"] = arrivals["origin_window_time"] + arrivals["travel_time"]


        last_allowed_arrival = ev_times + nth_tt_per_ev
        max_last_allowed_arrival = np.nanmax(last_allowed_arrival)
        window_end = max_last_allowed_arrival + ev_w_end_pad

        path ="/groups/igonin/ecastillo/UTDQuake/utdquake/utils/window_debug.png"
        plot_window_times(arrivals, 
                            # max_last_allowed_arrival, 
                            window_end, 
                           relative_per_event=True,
                           last_event_id=events["event_id"].iloc[-1],
                            save_path=path)

        arrivals = arrivals[arrivals["window_time"] <= window_end].reset_index(drop=True)

        # print("ev_times:", ev_times)
        # print("max_last_allowed_arrival:", max_last_allowed_arrival)
        # print("nth_tt_per_ev:",nth_tt_per_ev)

        if not arrivals.empty:
            # Merge stations into arrivals, keeping existing columns clean
            arrivals = arrivals.merge(
                self.stations[["station", "latitude", 
                                "longitude","elevation"]],
                on="station",
                how="left"
            )

            # Warn if any arrival has no latitude or longitude
            missing_coords = arrivals[
                arrivals["latitude"].isna() | arrivals["longitude"].isna()
            ]

            if not missing_coords.empty:
                missing_stations = missing_coords["station"].unique()
                print(
                    f"Warning: Missing latitude/longitude for stations: {list(missing_stations)}"
                )
        
        self.event_origins = events
        self.arrivals = arrivals

    def add_events(self, events):
        if not isinstance(events, (list, tuple)):
            events = [events]

        cat = obspy.Catalog(events=events)

        if len(cat) == 0:
            #warning
            print("Warning: No events to add.")
            return

        origins_df = get_preferred_origins(cat)
        self.event_origins = pd.concat([self.event_origins, origins_df], 
                                        ignore_index=True)

        arrivals_df = cat.arrivals_to_df()

        events_df = self.event_origins[["preferred_origin_id", 
                                "event_id"]].copy()
        # events_df.rename(columns={"time":"origin_time"}, inplace=True)

        arrivals_df = arrivals_df.merge(
            events_df,
            left_on="origin_id",
            right_on="preferred_origin_id",
            how="left",
        )

        # m5 = origins_df[origins_df["magnitude"] >= 5]["event_id"].unique()
        # arrivals_m5 = arrivals_df[arrivals_df["event_id"].isin(m5)]
        # print(m5)
        # print(len(arrivals_m5))

        

        picks_df = cat.picks_to_df()
        merged = merge_arrivals_and_picks(arrivals_df, picks_df)
        merged["travel_time"] = (
                    merged["time"] - merged["origin_time"]
                ).dt.total_seconds()
        

        self.arrivals = pd.concat([self.arrivals, merged], ignore_index=True)
        # arrivals_m5 = self.arrivals[self.arrivals["event_id"].isin(m5)]
        # print(len(arrivals_m5))
        # exit()
        self._update_timeline()

    def add_stations(self, stations):
        """
        """
        if 'latitude' not in stations.columns or 'longitude' not in stations.columns:
            raise ValueError(f"Columns 'latitude' or 'longitude' not found in stations dataframe")
        
        self.stations = pd.concat([self.stations, stations], ignore_index=True)

    def add_noise(self,random_range=(1, 500)):
        n_phases = random.randint(*random_range)

        noise = self.stations
        sta_in_window = self.arrivals["station"].unique()
        noise["weight"] = noise.apply(lambda x: 1 if x["station"] in sta_in_window else 0.05, axis=1)
        noise = noise.sample(n_phases, weights="weight", replace=True,ignore_index=True) 


        random_floats = [random.uniform(0, self.length+self.length * self.last_event_w) for _ in range(len(noise))]
        random_phases = np.random.choice(['P', 'S'], size=len(noise))

        noise["window_time"] = random_floats
        noise["phase"] = random_phases
        noise["author"] = "noise"

        noise = noise[["author","station", "window_time", "phase", "latitude", "longitude", "elevation"]]

        # print(noise)
        self.arrivals = pd.concat([self.arrivals, noise], ignore_index=True)

        # print(self.arrivals[self.arrivals["author"] == "noise"][["station", "window_time", "phase", "latitude", "longitude", "elevation"]])
        # print(self.arrivals[self.arrivals["author"] == "noise"])
        # exit()
        # self.arrivals = pd.concat([self.arrivals, noise], ignore_index=True)

    def plot_window(self,
                    reference_location=None,
                    show_earthquakes=True,
                    show_earthquake_lines=True,
                    show_phases="both",
                    show_moveout=True,
                    show_station_labels=True,
                    
                    show_legend=True,
                    save_path=None,
                    ax=None,
                    show=True):

        if self.arrivals.empty or self.event_origins.empty:
            print("No events or arrivals to plot.")
            return

        if self.stations.empty:
            raise ValueError(
                "Station coordinates not found. Please use eqw.add_stations() before plotting."
            )

        stations = self.stations
        arrivals = self.arrivals.copy()
        earthquakes = self.event_origins

        # ------------------------------------------------------
        # 1. Determine reference mode
        # ------------------------------------------------------
        if reference_location is None:
            local_reference = True
        else:
            local_reference = False
            ref_lat, ref_lon, ref_elv = reference_location

        # GLOBAL reference only used if reference_location is not None
        if not local_reference:
            arrivals["y"] = arrivals.apply(
                lambda row: gps2dist_azimuth(
                    ref_lat, ref_lon, row["latitude"], row["longitude"]
                )[0] / 1000,
                axis=1,
            )
        else:
            arrivals["y"] = np.nan  # filled per event

        # Clean NaN coordinates
        nan_coords = arrivals[arrivals["latitude"].isna() | arrivals["longitude"].isna()]
        if not nan_coords.empty:
            missing_stations = nan_coords["station"].unique()
            print(f"Warning: Missing latitude/longitude for stations: {list(missing_stations)}")

        arrivals = arrivals.dropna(subset=["latitude", "longitude"], ignore_index=True)

        event_ids = earthquakes.sort_values("window_time")
        event_ids =event_ids["event_id"].unique()
        phase_mask = {"P": ["P"], "S": ["S"], "both": ["P", "S"]}[show_phases]

        colors = plt.cm.tab20c(np.linspace(0, 1, len(event_ids)))
        color_map = dict(zip(event_ids, colors))

        if ax is None:
            fig, ax = plt.subplots(figsize=(8, 4))

        # ------------------------------------------------------
        # 2. Event loop
        # ------------------------------------------------------
        arrivals_noise = arrivals[arrivals["author"] == "noise"]
        # Plot noise arrivals
        


        max_y = []
        
        for e, event_id in enumerate(event_ids, 1):

            # Event origin time
            event_start = earthquakes.loc[earthquakes["event_id"] == event_id, "window_time"].values[0]
            arrivals_event = arrivals[arrivals["event_id"] == event_id].copy()

            arrivals_event = arrivals_event[arrivals_event["author"] != "noise"]

            # Earthquake info
            eq = earthquakes[earthquakes["event_id"] == event_id].iloc[0]
            eq_lat = eq["latitude"]
            eq_lon = eq["longitude"]

            # --------------------------------------------------
            # Reference handling
            # --------------------------------------------------
            if local_reference:
                # Earthquake itself is reference → y_eq = 0
                y_eq = 0
                arrivals_event["y"] = arrivals_event.apply(
                    lambda row: gps2dist_azimuth(
                        eq_lat, eq_lon, row["latitude"], row["longitude"]
                    )[0] / 1000,
                    axis=1,
                )
            else:
                # Global reference already computed earlier
                y_eq = gps2dist_azimuth(
                    ref_lat, ref_lon, eq_lat, eq_lon
                )[0] / 1000

            print(f"Event #{e}: M{eq['magnitude']}-{eq['time']}. t={event_start} s, y={y_eq:.2f} km")
            
            # color = color_map[event_id]

            # check if e is even or odd for color selection
            if e % 2 == 0:
                color = "#ec7524"  # orange
            else:
                color = "#007A33"  # green


            # --------------------------------------------------
            # 3. Plot earthquake star
            # --------------------------------------------------
            if show_earthquakes:
                ax.scatter(event_start, y_eq, marker="*",alpha=0.5,
                                    color=color, s=100, zorder=5)
                
                #plot vertical line from earthquake to bottom
                

            # --------------------------------------------------
            # 4. Plot arrivals
            # --------------------------------------------------
            moveout_lines = {}
            for phase in phase_mask:
                arrivals_phase = arrivals_event[arrivals_event["phase"] == phase].copy()
                if arrivals_phase.empty:
                    continue

                # x-position (moveout line)

                
                arrivals_phase["x"] = arrivals_phase["window_time"]

                # arrivals_phase = arrivals_phase[arrivals_phase["x"] <= event_start + self.length]

                # if phase == "P":
                    # color_arrival = "#ec7524"
                    
                # else:
                    # color_arrival = "#007A33"    

                color_arrival = color

                if show_moveout:
                    # Draw moveout line from earthquake to each arrival
                    how="interp"

                    _x = arrivals_phase["x"]
                    _y = arrivals_phase["y"]
                    _x = np.append(_x, event_start)
                    _y = np.append(_y, y_eq)

                    if how == "linear":
                        #add 0 point at event origin
                        slope, intercept, r_value, _, _ = linregress(_x, _y)

                        x_moveout = np.linspace(event_start, _x.max(), 100)
                        y_moveout = slope * (x_moveout - event_start) + y_eq
                    else:
                        sort_idx = np.argsort(_x)
                        _x_sorted = _x[sort_idx]
                        _y_sorted = _y[sort_idx]
                        x_moveout = np.linspace(event_start, _x.max(), 100)
                        y_moveout = np.interp(x_moveout, _x_sorted, _y_sorted)


                    moveout_lines[phase] = (x_moveout, y_moveout)
                    
                    ax.plot(x_moveout, y_moveout, linestyle="--", color=color,
                            linewidth=0.8,
                                alpha=0.5, zorder=1)




                for _, row in arrivals_phase.iterrows():
                    facecolor = color if row["phase"] == "P" else "none"
                    # facecolor = color_arrival
                    edgecolor = color_arrival
                    ax.scatter(
                        row["x"], row["y"], marker="o",
                        facecolors=facecolor, edgecolors=edgecolor, 
                        s=10,
                        zorder=10
                    )
                # print(arrivals_phase[["station", "phase", "x", "y"]])
                max_y.append(arrivals_phase["y"].max())

            if "P" in moveout_lines and "S" in moveout_lines:
                xP, yP = moveout_lines["P"]
                xS, yS = moveout_lines["S"]

                # Common x-range
                xmin = max(xP.min(), xS.min())
                xmax = min(xP.max(), xS.max())

                if xmin < xmax:  # ensure overlap exists
                    # Build one shared x grid
                    x_common = np.linspace(xmin, xmax, 200)

                    # Interpolate both curves onto the shared grid
                    yP_common = np.interp(x_common, xP, yP)
                    yS_common = np.interp(x_common, xS, yS)

                    # Fill the area
                    ax.fill_between(
                        x_common,
                        yP_common,
                        yS_common,
                        color=color,
                        alpha=0.1,
                        zorder=0
                    )
            # --------------------------------------------------
            # 5. Station labels
            # --------------------------------------------------
            if show_station_labels:
                arrivals_plot = arrivals_event[arrivals_event["phase"].isin(phase_mask)].copy()
                arrivals_plot["x"] = event_start + (
                    arrivals_plot["time"] - arrivals_plot["origin_time"]
                ).dt.total_seconds()

                for (net, sta), group in arrivals_plot.groupby(["network", "station"]):
                    if "P" in group["phase"].values:
                        row_label = group[group["phase"] == "P"].iloc[0]
                        x_offset = -5
                        ha = "right"
                    else:
                        row_label = group.iloc[0]
                        x_offset = 5
                        ha = "left"

                    ax.text(
                        row_label["x"] + x_offset, row_label["y"], sta,
                        verticalalignment="center", horizontalalignment=ha,
                        fontsize=9, color=color
                    )
        
        max_distance = max(max_y)
        y_noise = np.random.uniform(0, max_distance, 
                                    size=len(arrivals_noise))
        if not arrivals_noise.empty:
            ax.scatter(
                    arrivals_noise["window_time"], y_noise,
                        marker="o",
                        alpha=0.5,
                    facecolors="gray",  s=10,
                    zorder = 0
                )
            
        y_min, y_max = ax.get_ylim()
            
        if show_earthquake_lines:
            for e, event_id in enumerate(event_ids, 1):

                eq = earthquakes[earthquakes["event_id"] == event_id].iloc[0]
                event_start = eq["window_time"]
                magnitude = eq["magnitude"]
                origin_time = eq["time"]

                # Draw main vertical line
                ax.plot([event_start, event_start], [0, y_max],
                        color="gray", alpha=0.5, linewidth=1.6, zorder=1)

        ax.set_ylim(y_min, y_max)

        if show_legend:
            legend_elements = [
                    Line2D([0], [0], marker='o', color='gray', label='Noise', 
                        markerfacecolor='gray', markersize=8, linestyle='None'),
                    Line2D([0], [0], marker='o', color='#007A33', label='P', 
                        markerfacecolor='#007A33', markersize=8, linestyle='None'),
                    Line2D([0], [0], marker='o', color='#007A33', label='S', 
                        markerfacecolor="none", markersize=8, linestyle='None'),
                    Line2D([0], [0], marker='*', color="#ec7524", label='Earthquake', 
                        markerfacecolor="#ec7524", markersize=12, linestyle='None')
                ]

            ax.legend(handles=legend_elements, loc='lower left', framealpha=0.9)


        # ax.set_xlim(0, self.max_length)
        # ax.set_ylim(-10, max(max_y) + 5)
        #inver  axis
        ax.invert_yaxis()
        ax.xaxis.tick_top()
        ax.xaxis.set_label_position("top")

        ax.set_xlabel("Window time [s]")
        # ax.set_xlabel("Window time [s]", loc="left")
        ax.set_ylabel("Distance [km]")
        ax.grid(True, linestyle="--", alpha=0.5)
        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300)
        if show:
            plt.show()
        # else:
        #     plt.close(fig)
        
        return ax