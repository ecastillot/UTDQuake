import logging
import os
import pandas as pd
import obsplus
import time
from obspy import UTCDateTime
from utdquake.bank.fdsn import Client

logger = logging.getLogger("download_events")

starttime = UTCDateTime("2010-01-01T00:00:00")
endtime = UTCDateTime("2025-08-01T00:00:00")
bank_folder = "/groups/igonin/ecastillo/UTDBank/bank"
availability_path = "/groups/igonin/ecastillo/UTDQuake/data/info.csv"
stations_folder = "/groups/igonin/ecastillo/UTDBank/stations"

MAX_RETRIES = 5           # maximum retry attempts
WAIT_MINUTES = 5          # time to wait when rate-limited

availability = pd.read_csv(availability_path)
availability = availability[availability["picks"] == True]
availability = availability[availability["agency"] == "USGS"]

for i, row in availability.iterrows():

    

    agency = row["agency"]
    provider = row["url"]
    client = Client(base_url=provider)

    logger.info(f"Checking availability for {agency}-{provider}")

    try:
        contributors = client.services.get("available_event_contributors", [])
        if not contributors:
            logger.warning(f"No contributors found for {agency}-{provider}. Using contributor=None")
            contributors = [None]
    except Exception as e:
        logger.warning(f"Error getting contributors for {agency}-{provider}: {e}. Using contributor=None")
        contributors = [None]

    for contributor in contributors:
        logger.info(f"Downloading events for contributor: {agency}-{provider}-{contributor}")

        if contributor != "uw":
            continue

        # Output folder
        if contributor is None:
            contributor_events_folder = os.path.join(bank_folder, agency)
        else:
            contributor_events_folder = os.path.join(bank_folder, contributor)

        retries = 0
        while retries < MAX_RETRIES:
            try:
                client.download_events(
                    events_bank_path=contributor_events_folder,
                    starttime=starttime,
                    endtime=endtime,
                    path_structure='{year}/{month}/{day}',
                    name_structure='{event_id_end}',
                    patience=100,
                    chunk_seconds=86400,
                    max_n_events=5000,
                    max_from_bank=True,
                    calculate_d_az=True,
                    stations_bank_path=stations_folder,
                    reverse=True,
                    workers=50,
                    contributor=contributor
                )
                logger.info(f"Work concluded for {contributor} from {agency}-{provider}")
                break  # ✅ success → exit retry loop

            except Exception as e:
                error_str = str(e)

                # Detect rate limit (HTTP 429 or text from server)
                if "429" in error_str or "rate" in error_str.lower():
                    retries += 1
                    logger.error(
                        f"Rate limit reached for {contributor} ({agency}-{provider}) "
                        f"- attempt {retries}/{MAX_RETRIES}. Waiting {WAIT_MINUTES} minutes..."
                    )
                    time.sleep(WAIT_MINUTES * 60)
                    continue  # retry

                # ❌ Other error → do not retry this contributor
                logger.error(
                    f"Error downloading events for {contributor} from {agency}-{provider}: {e}"
                )
                break

        else:
            logger.error(
                f"Max retries reached ({MAX_RETRIES}) for {contributor} from {agency}-{provider}. Skipping..."
            )

    logger.info(f"Finished processing {agency}-{provider}")
