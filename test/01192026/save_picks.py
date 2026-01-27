import os 
os.environ["UTDQUAKE_ROOT"] = "/groups/igonin/ecastillo/UTDQuake"

import utdquake as utdq
from utdquake.core.cache import list_local_networks
import logging

logger = logging.getLogger(__name__)


# networks = list_local_networks()
networks = ["tx","RSNC"]

#reverse the list
networks = sorted(networks, reverse=True)

for net in networks:
    print(net)
    bank =  utdq.load_network(net) 
    bank.save_picks(replace=True)


