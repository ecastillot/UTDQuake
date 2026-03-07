import numpy as np

#: Default QC parameters for pick-level filtering in UTDQuake.
#: Passed to :func:`picks_qc` if `pick_qc_args=None` in
#: :func:`apply_utdquake_qc_to_catalog`.
#:
#: Keys
#: ----
#: - min_travel_time : float
#:     Minimum allowed travel time (seconds).
#: - min_linear_hyp_distance : float
#:     Minimum hypocentral distance (km).
#: - min_epicentral_distance : float
#:     Minimum epicentral distance (degrees).
#: - sp_threshold : dict of tuple -> tuple
#:     Phase pairs mapped to allowed S–P time difference ranges.
#:     Example: {("S", "P"): (0, np.inf)}
#: - debug : bool
#:     If True, prints debug information.
#: - apply_to_nans : bool
#:     If True, rows with NaNs in the QC columns are removed.
PICK_QC_DEFAULTS = {
    "min_travel_time": 0,
    "min_linear_hyp_distance": 0,
    "min_epicentral_distance": 0,
    "sp_threshold": {
        ("S", "P"): (0, np.inf),
        ("Sn", "Pn"): (0, np.inf),
        ("Sg", "Pg"): (0, np.inf),
    },
    "debug": False,
    "apply_to_nans": False,
}


#: Default QC parameters for event-level filtering in UTDQuake.
#: Passed to :func:`events_qc` if `event_qc_args=None` in
#: :func:`apply_utdquake_qc_to_catalog`.
#:
#: Keys
#: ----
#: - min_associated_phase_count : int
#:     Minimum number of associated phases per event.
#: - min_used_phase_count : int
#:     Minimum number of used phases per event.
#: - min_station_count : int
#:     Minimum number of stations per event.
#: - max_standard_error : float
#:     Maximum allowed event location standard error.
#: - debug : bool
#:     If True, prints debug information.
#: - apply_to_nans : bool
#:     If True, rows with NaNs in QC columns are removed.
EVENT_QC_DEFAULTS = {
    "min_associated_phase_count": 4,
    "min_used_phase_count": 4,
    "min_station_count": 3,
    "max_standard_error": 1.8,
    "debug": False,
    "apply_to_nans": False,
}


#: Default parameters for global trend filtering in UTDQuake.
#: P,Pn,Pg trend was obtained from us network, and S, Sn, Sg trend from AUST network.
GLOBAL_TRENDS_DEFAULTS_DEG2 = {
    "P": {
            "degree": 2,
            "coefficients": [
                -4.588170034538625e-06,
                0.1204498394083781,
                9.425437905735034
            ],
            "sigma_median": 3.081852707836243,
            "sigma_max": 18.122289219478738,
            "k": 5,
            "x_min": 0,
            "x_max": 11062.643551617337
        },
        "Pn": {
            "degree": 2,
            "coefficients": [
                -2.123100378455806e-06,
                0.1266681522352577,
                3.972939045543998
            ],
            "sigma_median": 2.3717707360038713,
            "sigma_max": 3.1788006095243153,
            "k": 5,
            "x_min": 0,
            "x_max": 1996.7077724459723
        },
        "Pg": {
            "degree": 2,
            "coefficients": [
                -3.778958404297257e-05,
                0.17071245733195828,
                0.1353941601365633
            ],
            "sigma_median": 0.7664360582262733,
            "sigma_max": 5.0462686049646654,
            "k": 5,
            "x_min": 0,
            "x_max": 728.2027580903004
        },
        "S": {
            "degree": 2,
            "coefficients": [
                -1.0258425351247499e-05,
                0.23111502668199244,
                6.210472294867918
            ],
            "sigma_median": 10.393477818397521,
            "sigma_max": 256.35044260025336,
            "k": 5,
            "x_min": 0,
            "x_max": 13506.250225497472
        },
        "Sn": {
            "degree": 2,
            "coefficients": [
                -2.3558552586659218e-05,
                0.2520839395599748,
                1.0803011315793982
            ],
            "sigma_median": 3.053158871586068,
            "sigma_max": 6.134819445258061,
            "k": 5,
            "x_min": 0,
            "x_max": 10504.929615655545
        },
        "Sg": {
            "degree": 2,
            "coefficients": [
                5.762396673402229e-06,
                0.2814509339071347,
                0.739648517284471
            ],
            "phase": "Sg",
            "sigma_median": 0.3828498082403183,
            "sigma_max": 0.965278331528081,
            "k": 3,
            "x_min": 0,
            "x_max": 885.351256561625,
        }
    }

#: Default parameters for global trend filtering in UTDQuake.
#: P,Pn,Pg trend was obtained from us network, and S, Sn, Sg trend from AUST network.
GLOBAL_TRENDS_DEFAULTS_DEG1 = {
    "P": {
        "coefficients": [
            0.07945741212769164,
            60.32603151127707
        ],
        "sigma_median": 7.0525733122093595,
        "sigma_max": 19.801861594870104,
        "k": 5,
        "degree": 1,
        "x_min": 1.0754613852665544,
        "x_max": 11062.643551617337
        
    },
    "Pn": {
        "coefficients": [
            0.12316349397703344,
            4.835650674225658
        ],
        "sigma_median": 2.327643142127425,
        "sigma_max": 2.9704320635081465,
        "k": 5,
        "degree": 1,
        "x_min": 39.740044840344225,
        "x_max": 1996.7077724459723
    },
    "Pg": {
        "coefficients": [
            0.15459825345901948,
            1.117844554622633
        ],
        "sigma_median": 3.106865855575151,
        "sigma_max": 6.355061897761255,
        "k": 5,
        "degree": 1,
        "x_min": 3.740794380573519,
        "x_max": 728.2027580903004
    },
    "S": {
        "coefficients": [
            0.2261926148374934,
            3.397333072682481
        ],
        "sigma_median": 3.578861180113502,
        "sigma_max": 7.2650538817134045,
        "k": 5,
        "degree": 1,
        "x_min": 2.075320817203789,
        "x_max": 1256.206257194874
    },
    "Sn": {
        "coefficients": [
            0.22162848462639803,
            6.037910844688636
        ],
        "sigma_median": 3.598439035557803,
        "sigma_max": 9.357424233986094,
        "k": 5,
        "degree": 1,
        "x_min": 49.024698859061346,
        "x_max": 1677.1449436139112
    },
    "Sg": {
        "coefficients": [
            0.26907127667113884,
            1.1107442939870609
        ],
        "sigma_median": 1.112657127952095,
        "sigma_max": 3.5700850518730123,
        "k": 5,
        "degree": 1,
        "x_min": 3.740794380573519,
        "x_max": 369.1684178094778
    }
}