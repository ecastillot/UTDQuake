import pandas as pd
import os
from utdquake.qc.travel_time import (
                                    TravelTime,
                                    TravelTimeModel)
# from utdquake.qc.plot import plot_tt_qc
from utdquake.writers.schema import sanitize_dataframe
import concurrent.futures as cf


fit = True
plot = True
max_workers = min(8, len(networks))  # adjust as needed
base_input = "/groups/igonin/ecastillo/UTDQuake/picks"
results_folder = f"/groups/igonin/ecastillo/UTDQuake/manifests/qc"

networks = os.listdir(base_input)
# networks = ["TAP","tx","uw","ok","nn","RSNC","nc","us"]
# networks = ["uw"]

print("Networks to process:", networks)


def process_network(network: str):
    print(f"Processing network: {network}")

    data_input = os.path.join(base_input, network)
    data_output = os.path.join(results_folder, "picks", network)
    model_path = os.path.join(results_folder, "qc_pick_models", network)

    # Ensure directories exist
    os.makedirs(os.path.dirname(data_output), exist_ok=True)
    os.makedirs(os.path.dirname(model_path), exist_ok=True)

    try:
        if fit:
            df = pd.read_parquet(data_input)

            multi_qc = TravelTime(df)
            multi_qc.clean_data(
                use_global=True,
                use_mahalanobis=False,
            )
            multi_qc.build_bins(n_bins=100, dmin=0, dmax=30e3, alpha=3.0)
            multi_qc.build_models(min_points_per_bin=4)

            df_qc_z = multi_qc.attach_zscore()
            sanitized_df = sanitize_dataframe(df_qc_z, order_cols="picks")

            sanitized_df.to_parquet(data_output, index=False)
            multi_qc.save_models_combined(model_path)

        return f"✅ Done: {network}"

    except Exception as e:
        return f"❌ Error in {network}: {e}"

if max_workers == 1:
    for network in networks:
        result = process_network(network)

else:
    with cf.ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = list(executor.map(process_network, networks))
        for r in results:
            print(r)

    # if plot:
    #     # df = pd.read_csv(data_input)
    #     df = pd.read_parquet(data_input)
    #     load = TravelTimeModel.load(model_path)
    #     models = load.models
        
    #     plot_tt_qc(df, models=models, 
    #                add_inset=True, 
    #                savepath=fig_path)



                                            
    
