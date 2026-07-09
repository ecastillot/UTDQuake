import os 
os.environ["HF_DATASETS_PARALLELISM"] = "false"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["UTDQUAKE_ROOT"] = "/groups/igonin/ecastillo/UTDQuake"
os.environ["UTDQUAKE_DAS_ROOT"] = "/groups/igonin/ecastillo/UTDQuake_DAS"

from pathlib import Path
from obsplus import EventBank
from utdquake.bank.bank import UTDQBank
import concurrent.futures as cf

previous_name = "GCI"
new_name = "UWF"
chunk_size = 10
max_workers = 50

bank_path = Path(os.environ["UTDQUAKE_DAS_ROOT"])/"banks_DAS"/previous_name
bank = UTDQBank(bank_path)

new_bank_path = Path(os.environ["UTDQUAKE_DAS_ROOT"])/"banks_DAS"/new_name
new_bank = EventBank(new_bank_path,
                     path_structure='{year}/{month}/{day}',
                    name_structure='{event_id_end}',
                    format='quakeml')



def update_pick(pick):
    pick.waveform_id.network_code = new_name
    return pick

print(bank)
events = bank.read_index()
event_ids = events["event_id"].tolist()
for i in range(0, len(event_ids), chunk_size):

    print(f"Processing chunk {i // chunk_size + 1} of {len(event_ids) // chunk_size + 1}")
    ids_chunk = event_ids[i:i + chunk_size]

    # Retrieve all events in the chunk
    cat = bank.get_events(event_id=ids_chunk)

    # Update network code for every pick in every event
    new_events = []
    for event in cat:
        picks = event.picks

    #     for pick in event.picks:
    #         pick.waveform_id.network_code = new_name

        with cf.ThreadPoolExecutor(max_workers=max_workers) as executor:
            updated_picks = list(executor.map(update_pick, picks))
            new_picks = updated_picks

        event.picks = new_picks
        new_events.append(event)

    cat.events = new_events
    # Save the modified catalog
    new_bank.put_events(cat)

