import logging
import os
import pandas as pd
import obsplus
import time
from obspy import UTCDateTime
from utdquake.bank.fdsn import Client
from datetime import datetime

logger = logging.getLogger("download_events")

# -------------------------
# USER CONFIG
# -------------------------
starttime = UTCDateTime("2010-01-01T00:00:00")
endtime = UTCDateTime("2021-07-03 07:24:17.460000") # KRSC last event
# endtime = UTCDateTime("2024-02-14T00:00:00") # DAGSR last event
bank_folder = "/groups/igonin/ecastillo/UTDQuake/test/10132025/bank_test"
availability_path = "/groups/igonin/ecastillo/UTDQuake/data/info.csv"
stations_folder = "/groups/igonin/ecastillo/Bank/stations"

PROGRESS_CSV = "/groups/igonin/ecastillo/UTDQuake/data/progress_events.csv"

MAX_RETRIES = 5
WAIT_MINUTES = 5

# -------------------------
# LOAD AVAILABILITY
# -------------------------
availability = pd.read_csv(availability_path)
availability = availability[(availability["picks"] == True)]
availability = availability[(availability["agency"] != "USGS")]

# -------------------------
# PROGRESS TRACKER
# -------------------------
def load_progress():
    if os.path.exists(PROGRESS_CSV):
        return pd.read_csv(PROGRESS_CSV)
    else:
        return pd.DataFrame(columns=["agency", "provider", "contributor", 
                                     "status", "last_update", "notes"])

def save_progress(progress_df):
    progress_df.to_csv(PROGRESS_CSV, index=False)

def update_progress(progress_df, agency, provider, contributor, status, notes=""):
    now = datetime.utcnow().isoformat()
    row_idx = progress_df[
        (progress_df.agency == agency) &
        (progress_df.provider == provider) &
        (progress_df.contributor == str(contributor))
    ].index

    if len(row_idx) == 0:
        new_row = {
            "agency": agency,
            "provider": provider,
            "contributor": str(contributor),
            "status": status,
            "last_update": now,
            "notes": notes
        }
        progress_df = pd.concat([progress_df, pd.DataFrame([new_row])], ignore_index=True)
    else:
        progress_df.loc[row_idx, "status"] = status
        progress_df.loc[row_idx, "last_update"] = now
        progress_df.loc[row_idx, "notes"] = notes

    save_progress(progress_df)
    return progress_df

progress_df = load_progress()


# -------------------------
# MAIN LOOP
# -------------------------

for i, row in availability.iterrows():
    agency = row["agency"]
    provider = row["url"]
    client = Client(base_url=provider)

    logger.info(f"Checking availability for {agency}-{provider}")

    # get contributors
    try:
        contributors = client.services.get("available_event_contributors", [])
        if not contributors:
            contributors = [None]
    except Exception as e:
        logger.warning(f"Error getting contributors: {e}. Using contributor=None")
        contributors = [None]

    for contributor in contributors:
        # CHECK IF ALREADY DONE
        # done_mask = (
        #     (progress_df.agency == agency) &
        #     (progress_df.provider == provider) &
        #     (progress_df.contributor == str(contributor)) &
        #     (progress_df.status == "done")
        # )
        # if done_mask.any():
        #     logger.info(f"Skipping {agency}-{provider}-{contributor}: already done")
        #     continue

        # if contributor != "DAGSR":
        #     continue

        if contributor != "KRSC":
            continue

        logger.info(f"Downloading events for contributor: {agency}-{provider}-{contributor}")

        if contributor is None:
            contributor_events_folder = os.path.join(bank_folder, agency)
        else:
            contributor_events_folder = os.path.join(bank_folder, contributor)

        retries = 0
        progress_df = update_progress(progress_df, agency, provider, contributor, "running")

        while retries < MAX_RETRIES:
            try:
                client.download_events(
                    events_bank_path=contributor_events_folder,
                    starttime=starttime,
                    endtime=endtime,
                    path_structure='{year}/{month}/{day}',
                    name_structure='{event_id_end}',
                    patience=int(365*10), 
                    chunk_seconds=86400,
                    max_n_events=5000,
                    max_from_bank=True,
                    calculate_d_az=True,
                    stations_bank_path=stations_folder,
                    reverse=True,
                    workers=50,
                    contributor=contributor,
                )

                logger.info(f"Completed {contributor} from {agency}-{provider}")
                progress_df = update_progress(progress_df, agency, provider, contributor, "done")
                break

            except Exception as e:
                error_str = str(e)

                if "429" in error_str or "rate" in error_str.lower():
                    retries += 1
                    logger.error(
                        f"Rate limit for {contributor} ({agency}-{provider}) "
                        f"- attempt {retries}/{MAX_RETRIES}. Waiting {WAIT_MINUTES} min..."
                    )
                    progress_df = update_progress(
                        progress_df, agency, provider, contributor, 
                        "retrying", notes=f"rate limit retry {retries}"
                    )
                    time.sleep(WAIT_MINUTES * 60)
                    continue

                logger.error(f"Error for {contributor}: {e}")
                progress_df = update_progress(
                    progress_df, agency, provider, contributor,
                    "error", notes=str(e)
                )
                break

        else:
            # Retries exhausted
            logger.error(f"Max retries reached for {contributor}")
            progress_df = update_progress(
                progress_df, agency, provider, contributor,
                "error", notes="max retries exceeded"
            )

    logger.info(f"Finished processing {agency}-{provider}")
