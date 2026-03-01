import pandas as pd
from utdquake.qc.phase_cleaner import PhaseCleaner


df = pd.read_parquet("/groups/igonin/ecastillo/UTDQuake/picks/network=TAP.parquet")

df = df.dropna(subset=["linear_hyp_distance", "travel_time", "phase"])

# Keep only relevant columns
phase_order = ["P", "Pn", "Pg", "S", "Sn", "Sg"]
# k_dict = {
#     "P": (20, 25), "Pn": (20, 25), "Pg": (20, 25),
#     "S": (20, 25), "Sn": (20, 25), "Sg": (20, 25)
# }

k_dict = {
    "P": 2, "Pn": 2, "Pg": 2,
    "S": 2, "Sn": 2, "Sg": 2
}

cleaner = PhaseCleaner(phase_order=phase_order, k_dict=k_dict, min_points=20)


# global_trends_path = "/groups/igonin/ecastillo/utdquake/utdquake/qc/global_trends.json"
cleaned_df, removed_df = cleaner.filter_all_phases(df, 
                                                #    export_json_path=global_trends_path,
                                                degree=2
                                                   )

print("Kept picks:", len(cleaned_df))
print("Removed picks:", len(removed_df))


# Original counts for reference in the plots
original_counts = df["phase"].value_counts().to_dict()
print("Original counts:", original_counts)

fig, axes = cleaner.plot_all_phases(df, figsize=(8, 12), original_counts=original_counts,
                                    show_global_trend=True, degree=2)

# Save figure
fig.savefig("/groups/igonin/ecastillo/utdquake/scripts/qc/picks/2qc_picks.png", dpi=300)