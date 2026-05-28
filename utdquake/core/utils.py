import numpy as np
from typing import Optional

def merge_network_stats(all_stats: dict, distance_bins: Optional[list] = None) -> dict:
    """
    Merge statistics from multiple networks into a single stats dictionary.

    Parameters
    ----------
    all_stats : dict
        Dictionary of network stats, {network_name: stats_dict}.
    distance_bins : list, optional
        Distance bins to use. If None, default bins are used.

    Returns
    -------
    merged_stats : dict
        Single merged stats dictionary suitable for plotting.
    """
    merged_stats = {}

    # Merge arrays by concatenation
    merged_stats["depth_values"] = np.concatenate([s["depth_values"] for s in all_stats.values()])
    merged_stats["magnitude_values"] = np.concatenate([s["magnitude_values"] for s in all_stats.values()])
    merged_stats["distance_bins"] = distance_bins if distance_bins is not None else [0, 30, 60, 100, 150, 200, 300, 500, np.inf]

    # Sum counts for epicentral/hypocentral distances
    merged_stats["epi_dist_counts_P"] = np.sum([s["epi_dist_counts_P"] for s in all_stats.values()], axis=0)
    merged_stats["epi_dist_counts_S"] = np.sum([s["epi_dist_counts_S"] for s in all_stats.values()], axis=0)
    merged_stats["hyp_dist_counts_P"] = np.sum([s["hyp_dist_counts_P"] for s in all_stats.values()], axis=0)
    merged_stats["hyp_dist_counts_S"] = np.sum([s["hyp_dist_counts_S"] for s in all_stats.values()], axis=0)

    # Azimuthal gap
    merged_stats["az_gap_counts"] = np.sum([s["az_gap_counts"] for s in all_stats.values()], axis=0)
    merged_stats["az_gap_bins"] = all_stats[next(iter(all_stats))]["az_gap_bins"]  # Use bins from the first network

    # Azimuth
    merged_stats["azimuth_counts"] = np.sum([s["azimuth_counts"] for s in all_stats.values()], axis=0)
    merged_stats["azimuth_bins"] = all_stats[next(iter(all_stats))]["azimuth_bins"]  # Use bins from the first network
    
    return merged_stats