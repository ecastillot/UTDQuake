.. _overview-section:
Overview
=========================

For each UTDQuake network in :ref:`overview-seismic-data` and :ref:`overview-DAS-data`, a dedicated
collection of figures is generated. Each row gives the network's ``utdq_net`` code (the key used in
every table, see :ref:`dataset-naming-subsection`), the catalog its events come from and the
UTDQuake version that first added it (see :ref:`versions-section`). Click on
**Open Folder** to explore the full figure collection.

.. warning::

   All these figures can be created by network, see plot functions in :func:`utdquake.Network`,
   or with more flexibility for your own plots check :func:`utdquake.utils.plot` module.

.. _overview-seismic-data:
Seismic Data
----------------------

.. raw:: html

   <div align="center">

.. list-table:: Available Networks
   :widths: 12 20 8 25 30
   :header-rows: 1

   * - utdq_net
     - Catalog
     - Version
     - Figures Folder
     - Preview

   * - ak
     - ComCat
     - v1
     - `Open Folder <https://github.com/ecastillot/UTDQuake/tree/figures/figures/networks/ak>`_
     - .. image:: https://raw.githubusercontent.com/ecastillot/UTDQuake/figures/figures/networks/ak/ak_overview.png
          :width: 200px

   * - at
     - ComCat
     - v1
     - `Open Folder <https://github.com/ecastillot/UTDQuake/tree/figures/figures/networks/at>`_
     - .. image:: https://raw.githubusercontent.com/ecastillot/UTDQuake/figures/figures/networks/at/at_overview.png
          :width: 200px

   * - av
     - ComCat
     - v1
     - `Open Folder <https://github.com/ecastillot/UTDQuake/tree/figures/figures/networks/av>`_
     - .. image:: https://raw.githubusercontent.com/ecastillot/UTDQuake/figures/figures/networks/av/av_overview.png
          :width: 200px

   * - hv
     - ComCat
     - v1
     - `Open Folder <https://github.com/ecastillot/UTDQuake/tree/figures/figures/networks/hv>`_
     - .. image:: https://raw.githubusercontent.com/ecastillot/UTDQuake/figures/figures/networks/hv/hv_overview.png
          :width: 200px

   * - mb
     - ComCat
     - v1
     - `Open Folder <https://github.com/ecastillot/UTDQuake/tree/figures/figures/networks/mb>`_
     - .. image:: https://raw.githubusercontent.com/ecastillot/UTDQuake/figures/figures/networks/mb/mb_overview.png
          :width: 200px

   * - nc
     - ComCat
     - v1
     - `Open Folder <https://github.com/ecastillot/UTDQuake/tree/figures/figures/networks/nc>`_
     - .. image:: https://raw.githubusercontent.com/ecastillot/UTDQuake/figures/figures/networks/nc/nc_overview.png
          :width: 200px

   * - nm
     - ComCat
     - v1
     - `Open Folder <https://github.com/ecastillot/UTDQuake/tree/figures/figures/networks/nm>`_
     - .. image:: https://raw.githubusercontent.com/ecastillot/UTDQuake/figures/figures/networks/nm/nm_overview.png
          :width: 200px

   * - nn
     - ComCat
     - v1
     - `Open Folder <https://github.com/ecastillot/UTDQuake/tree/figures/figures/networks/nn>`_
     - .. image:: https://raw.githubusercontent.com/ecastillot/UTDQuake/figures/figures/networks/nn/nn_overview.png
          :width: 200px

   * - ok
     - ComCat
     - v1
     - `Open Folder <https://github.com/ecastillot/UTDQuake/tree/figures/figures/networks/ok>`_
     - .. image:: https://raw.githubusercontent.com/ecastillot/UTDQuake/figures/figures/networks/ok/ok_overview.png
          :width: 200px

   * - pr
     - ComCat
     - v1
     - `Open Folder <https://github.com/ecastillot/UTDQuake/tree/figures/figures/networks/pr>`_
     - .. image:: https://raw.githubusercontent.com/ecastillot/UTDQuake/figures/figures/networks/pr/pr_overview.png
          :width: 200px

   * - se
     - ComCat
     - v1
     - `Open Folder <https://github.com/ecastillot/UTDQuake/tree/figures/figures/networks/se>`_
     - .. image:: https://raw.githubusercontent.com/ecastillot/UTDQuake/figures/figures/networks/se/se_overview.png
          :width: 200px

   * - tx
     - ComCat
     - v1
     - `Open Folder <https://github.com/ecastillot/UTDQuake/tree/figures/figures/networks/tx>`_
     - .. image:: https://raw.githubusercontent.com/ecastillot/UTDQuake/figures/figures/networks/tx/tx_overview.png
          :width: 200px

   * - us
     - ComCat
     - v1
     - `Open Folder <https://github.com/ecastillot/UTDQuake/tree/figures/figures/networks/us>`_
     - .. image:: https://raw.githubusercontent.com/ecastillot/UTDQuake/figures/figures/networks/us/us_overview.png
          :width: 200px

   * - uu
     - ComCat
     - v1
     - `Open Folder <https://github.com/ecastillot/UTDQuake/tree/figures/figures/networks/uu>`_
     - .. image:: https://raw.githubusercontent.com/ecastillot/UTDQuake/figures/figures/networks/uu/uu_overview.png
          :width: 200px

   * - uw
     - ComCat
     - v1
     - `Open Folder <https://github.com/ecastillot/UTDQuake/tree/figures/figures/networks/uw>`_
     - .. image:: https://raw.githubusercontent.com/ecastillot/UTDQuake/figures/figures/networks/uw/uw_overview.png
          :width: 200px

   * - admin
     - ComCat
     - v1
     - `Open Folder <https://github.com/ecastillot/UTDQuake/tree/figures/figures/networks/admin>`_
     - .. image:: https://raw.githubusercontent.com/ecastillot/UTDQuake/figures/figures/networks/admin/admin_overview.png
          :width: 200px

   * - AEIC
     - ISC Bulletin
     - v1
     - `Open Folder <https://github.com/ecastillot/UTDQuake/tree/figures/figures/networks/AEIC>`_
     - .. image:: https://raw.githubusercontent.com/ecastillot/UTDQuake/figures/figures/networks/AEIC/AEIC_overview.png
          :width: 200px

   * - AFAD
     - ISC Bulletin
     - v1
     - `Open Folder <https://github.com/ecastillot/UTDQuake/tree/figures/figures/networks/AFAD>`_
     - .. image:: https://raw.githubusercontent.com/ecastillot/UTDQuake/figures/figures/networks/AFAD/AFAD_overview.png
          :width: 200px

   * - ANF
     - ISC Bulletin
     - v1
     - `Open Folder <https://github.com/ecastillot/UTDQuake/tree/figures/figures/networks/ANF>`_
     - .. image:: https://raw.githubusercontent.com/ecastillot/UTDQuake/figures/figures/networks/ANF/ANF_overview.png
          :width: 200px

   * - ATH
     - ISC Bulletin
     - v1
     - `Open Folder <https://github.com/ecastillot/UTDQuake/tree/figures/figures/networks/ATH>`_
     - .. image:: https://raw.githubusercontent.com/ecastillot/UTDQuake/figures/figures/networks/ATH/ATH_overview.png
          :width: 200px

   * - AUST
     - ISC Bulletin
     - v1
     - `Open Folder <https://github.com/ecastillot/UTDQuake/tree/figures/figures/networks/AUST>`_
     - .. image:: https://raw.githubusercontent.com/ecastillot/UTDQuake/figures/figures/networks/AUST/AUST_overview.png
          :width: 200px

   * - BEO
     - ISC Bulletin
     - v1
     - `Open Folder <https://github.com/ecastillot/UTDQuake/tree/figures/figures/networks/BEO>`_
     - .. image:: https://raw.githubusercontent.com/ecastillot/UTDQuake/figures/figures/networks/BEO/BEO_overview.png
          :width: 200px

   * - BER
     - ISC Bulletin
     - v1
     - `Open Folder <https://github.com/ecastillot/UTDQuake/tree/figures/figures/networks/BER>`_
     - .. image:: https://raw.githubusercontent.com/ecastillot/UTDQuake/figures/figures/networks/BER/BER_overview.png
          :width: 200px

   * - BGS
     - ISC Bulletin
     - v1
     - `Open Folder <https://github.com/ecastillot/UTDQuake/tree/figures/figures/networks/BGS>`_
     - .. image:: https://raw.githubusercontent.com/ecastillot/UTDQuake/figures/figures/networks/BGS/BGS_overview.png
          :width: 200px

   * - BUC
     - ISC Bulletin
     - v1
     - `Open Folder <https://github.com/ecastillot/UTDQuake/tree/figures/figures/networks/BUC>`_
     - .. image:: https://raw.githubusercontent.com/ecastillot/UTDQuake/figures/figures/networks/BUC/BUC_overview.png
          :width: 200px

   * - BYKL
     - ISC Bulletin
     - v1
     - `Open Folder <https://github.com/ecastillot/UTDQuake/tree/figures/figures/networks/BYKL>`_
     - .. image:: https://raw.githubusercontent.com/ecastillot/UTDQuake/figures/figures/networks/BYKL/BYKL_overview.png
          :width: 200px

   * - CATAC
     - ISC Bulletin
     - v1
     - `Open Folder <https://github.com/ecastillot/UTDQuake/tree/figures/figures/networks/CATAC>`_
     - .. image:: https://raw.githubusercontent.com/ecastillot/UTDQuake/figures/figures/networks/CATAC/CATAC_overview.png
          :width: 200px

   * - CNRM
     - ISC Bulletin
     - v1
     - `Open Folder <https://github.com/ecastillot/UTDQuake/tree/figures/figures/networks/CNRM>`_
     - .. image:: https://raw.githubusercontent.com/ecastillot/UTDQuake/figures/figures/networks/CNRM/CNRM_overview.png
          :width: 200px

   * - DJA
     - ISC Bulletin
     - v1
     - `Open Folder <https://github.com/ecastillot/UTDQuake/tree/figures/figures/networks/DJA>`_
     - .. image:: https://raw.githubusercontent.com/ecastillot/UTDQuake/figures/figures/networks/DJA/DJA_overview.png
          :width: 200px

   * - EAF
     - ISC Bulletin
     - v1
     - `Open Folder <https://github.com/ecastillot/UTDQuake/tree/figures/figures/networks/EAF>`_
     - .. image:: https://raw.githubusercontent.com/ecastillot/UTDQuake/figures/figures/networks/EAF/EAF_overview.png
          :width: 200px

   * - ECX
     - ISC Bulletin
     - v1
     - `Open Folder <https://github.com/ecastillot/UTDQuake/tree/figures/figures/networks/ECX>`_
     - .. image:: https://raw.githubusercontent.com/ecastillot/UTDQuake/figures/figures/networks/ECX/ECX_overview.png
          :width: 200px

   * - EST
     - ISC Bulletin
     - v1
     - `Open Folder <https://github.com/ecastillot/UTDQuake/tree/figures/figures/networks/EST>`_
     - .. image:: https://raw.githubusercontent.com/ecastillot/UTDQuake/figures/figures/networks/EST/EST_overview.png
          :width: 200px

   * - ETH
     - ETH
     - v1
     - `Open Folder <https://github.com/ecastillot/UTDQuake/tree/figures/figures/networks/ETH>`_
     - .. image:: https://raw.githubusercontent.com/ecastillot/UTDQuake/figures/figures/networks/ETH/ETH_overview.png
          :width: 200px

   * - FUNV
     - ISC Bulletin
     - v1
     - `Open Folder <https://github.com/ecastillot/UTDQuake/tree/figures/figures/networks/FUNV>`_
     - .. image:: https://raw.githubusercontent.com/ecastillot/UTDQuake/figures/figures/networks/FUNV/FUNV_overview.png
          :width: 200px

   * - GCG
     - ISC Bulletin
     - v1
     - `Open Folder <https://github.com/ecastillot/UTDQuake/tree/figures/figures/networks/GCG>`_
     - .. image:: https://raw.githubusercontent.com/ecastillot/UTDQuake/figures/figures/networks/GCG/GCG_overview.png
          :width: 200px

   * - GEOFON
     - GEOFON
     - v1
     - `Open Folder <https://github.com/ecastillot/UTDQuake/tree/figures/figures/networks/GEOFON>`_
     - .. image:: https://raw.githubusercontent.com/ecastillot/UTDQuake/figures/figures/networks/GEOFON/GEOFON_overview.png
          :width: 200px

   * - GFZ
     - ISC Bulletin
     - v1
     - `Open Folder <https://github.com/ecastillot/UTDQuake/tree/figures/figures/networks/GFZ>`_
     - .. image:: https://raw.githubusercontent.com/ecastillot/UTDQuake/figures/figures/networks/GFZ/GFZ_overview.png
          :width: 200px

   * - GII
     - ISC Bulletin
     - v1
     - `Open Folder <https://github.com/ecastillot/UTDQuake/tree/figures/figures/networks/GII>`_
     - .. image:: https://raw.githubusercontent.com/ecastillot/UTDQuake/figures/figures/networks/GII/GII_overview.png
          :width: 200px

   * - HEL
     - ISC Bulletin
     - v1
     - `Open Folder <https://github.com/ecastillot/UTDQuake/tree/figures/figures/networks/HEL>`_
     - .. image:: https://raw.githubusercontent.com/ecastillot/UTDQuake/figures/figures/networks/HEL/HEL_overview.png
          :width: 200px

   * - IDC
     - ISC Bulletin
     - v1
     - `Open Folder <https://github.com/ecastillot/UTDQuake/tree/figures/figures/networks/IDC>`_
     - .. image:: https://raw.githubusercontent.com/ecastillot/UTDQuake/figures/figures/networks/IDC/IDC_overview.png
          :width: 200px

   * - IGQ
     - ISC Bulletin
     - v1
     - `Open Folder <https://github.com/ecastillot/UTDQuake/tree/figures/figures/networks/IGQ>`_
     - .. image:: https://raw.githubusercontent.com/ecastillot/UTDQuake/figures/figures/networks/IGQ/IGQ_overview.png
          :width: 200px

   * - INET
     - ISC Bulletin
     - v1
     - `Open Folder <https://github.com/ecastillot/UTDQuake/tree/figures/figures/networks/INET>`_
     - .. image:: https://raw.githubusercontent.com/ecastillot/UTDQuake/figures/figures/networks/INET/INET_overview.png
          :width: 200px

   * - INMG
     - ISC Bulletin
     - v1
     - `Open Folder <https://github.com/ecastillot/UTDQuake/tree/figures/figures/networks/INMG>`_
     - .. image:: https://raw.githubusercontent.com/ecastillot/UTDQuake/figures/figures/networks/INMG/INMG_overview.png
          :width: 200px

   * - IPGP
     - ISC Bulletin
     - v1
     - `Open Folder <https://github.com/ecastillot/UTDQuake/tree/figures/figures/networks/IPGP>`_
     - .. image:: https://raw.githubusercontent.com/ecastillot/UTDQuake/figures/figures/networks/IPGP/IPGP_overview.png
          :width: 200px

   * - ISC
     - ISC Bulletin
     - v1
     - `Open Folder <https://github.com/ecastillot/UTDQuake/tree/figures/figures/networks/ISC>`_
     - .. image:: https://raw.githubusercontent.com/ecastillot/UTDQuake/figures/figures/networks/ISC/ISC_overview.png
          :width: 200px

   * - ISK
     - ISC Bulletin
     - v1
     - `Open Folder <https://github.com/ecastillot/UTDQuake/tree/figures/figures/networks/ISK>`_
     - .. image:: https://raw.githubusercontent.com/ecastillot/UTDQuake/figures/figures/networks/ISK/ISK_overview.png
          :width: 200px

   * - ISN
     - ISC Bulletin
     - v1
     - `Open Folder <https://github.com/ecastillot/UTDQuake/tree/figures/figures/networks/ISN>`_
     - .. image:: https://raw.githubusercontent.com/ecastillot/UTDQuake/figures/figures/networks/ISN/ISN_overview.png
          :width: 200px

   * - JAPAN
     - JMA
     - v1
     - `Open Folder <https://github.com/ecastillot/UTDQuake/tree/figures/figures/networks/JAPAN>`_
     - .. image:: https://raw.githubusercontent.com/ecastillot/UTDQuake/figures/figures/networks/JAPAN/JAPAN_overview.png
          :width: 200px

   * - JSN
     - ISC Bulletin
     - v1
     - `Open Folder <https://github.com/ecastillot/UTDQuake/tree/figures/figures/networks/JSN>`_
     - .. image:: https://raw.githubusercontent.com/ecastillot/UTDQuake/figures/figures/networks/JSN/JSN_overview.png
          :width: 200px

   * - KMA
     - ISC Bulletin
     - v1
     - `Open Folder <https://github.com/ecastillot/UTDQuake/tree/figures/figures/networks/KMA>`_
     - .. image:: https://raw.githubusercontent.com/ecastillot/UTDQuake/figures/figures/networks/KMA/KMA_overview.png
          :width: 200px

   * - KNET
     - ISC Bulletin
     - v1
     - `Open Folder <https://github.com/ecastillot/UTDQuake/tree/figures/figures/networks/KNET>`_
     - .. image:: https://raw.githubusercontent.com/ecastillot/UTDQuake/figures/figures/networks/KNET/KNET_overview.png
          :width: 200px

   * - KRNET
     - ISC Bulletin
     - v1
     - `Open Folder <https://github.com/ecastillot/UTDQuake/tree/figures/figures/networks/KRNET>`_
     - .. image:: https://raw.githubusercontent.com/ecastillot/UTDQuake/figures/figures/networks/KRNET/KRNET_overview.png
          :width: 200px

   * - KRSC
     - ISC Bulletin
     - v1
     - `Open Folder <https://github.com/ecastillot/UTDQuake/tree/figures/figures/networks/KRSC>`_
     - .. image:: https://raw.githubusercontent.com/ecastillot/UTDQuake/figures/figures/networks/KRSC/KRSC_overview.png
          :width: 200px

   * - KRSZO
     - ISC Bulletin
     - v1
     - `Open Folder <https://github.com/ecastillot/UTDQuake/tree/figures/figures/networks/KRSZO>`_
     - .. image:: https://raw.githubusercontent.com/ecastillot/UTDQuake/figures/figures/networks/KRSZO/KRSZO_overview.png
          :width: 200px

   * - LDG
     - ISC Bulletin
     - v1
     - `Open Folder <https://github.com/ecastillot/UTDQuake/tree/figures/figures/networks/LDG>`_
     - .. image:: https://raw.githubusercontent.com/ecastillot/UTDQuake/figures/figures/networks/LDG/LDG_overview.png
          :width: 200px

   * - MDD
     - ISC Bulletin
     - v1
     - `Open Folder <https://github.com/ecastillot/UTDQuake/tree/figures/figures/networks/MDD>`_
     - .. image:: https://raw.githubusercontent.com/ecastillot/UTDQuake/figures/figures/networks/MDD/MDD_overview.png
          :width: 200px

   * - MEX
     - ISC Bulletin
     - v1
     - `Open Folder <https://github.com/ecastillot/UTDQuake/tree/figures/figures/networks/MEX>`_
     - .. image:: https://raw.githubusercontent.com/ecastillot/UTDQuake/figures/figures/networks/MEX/MEX_overview.png
          :width: 200px

   * - MRB
     - ISC Bulletin
     - v1
     - `Open Folder <https://github.com/ecastillot/UTDQuake/tree/figures/figures/networks/MRB>`_
     - .. image:: https://raw.githubusercontent.com/ecastillot/UTDQuake/figures/figures/networks/MRB/MRB_overview.png
          :width: 200px

   * - NIC
     - ISC Bulletin
     - v1
     - `Open Folder <https://github.com/ecastillot/UTDQuake/tree/figures/figures/networks/NIC>`_
     - .. image:: https://raw.githubusercontent.com/ecastillot/UTDQuake/figures/figures/networks/NIC/NIC_overview.png
          :width: 200px

   * - NNC
     - ISC Bulletin
     - v1
     - `Open Folder <https://github.com/ecastillot/UTDQuake/tree/figures/figures/networks/NNC>`_
     - .. image:: https://raw.githubusercontent.com/ecastillot/UTDQuake/figures/figures/networks/NNC/NNC_overview.png
          :width: 200px

   * - NOA
     - ISC Bulletin
     - v1
     - `Open Folder <https://github.com/ecastillot/UTDQuake/tree/figures/figures/networks/NOA>`_
     - .. image:: https://raw.githubusercontent.com/ecastillot/UTDQuake/figures/figures/networks/NOA/NOA_overview.png
          :width: 200px

   * - NOU
     - ISC Bulletin
     - v1
     - `Open Folder <https://github.com/ecastillot/UTDQuake/tree/figures/figures/networks/NOU>`_
     - .. image:: https://raw.githubusercontent.com/ecastillot/UTDQuake/figures/figures/networks/NOU/NOU_overview.png
          :width: 200px

   * - OSPL
     - ISC Bulletin
     - v1
     - `Open Folder <https://github.com/ecastillot/UTDQuake/tree/figures/figures/networks/OSPL>`_
     - .. image:: https://raw.githubusercontent.com/ecastillot/UTDQuake/figures/figures/networks/OSPL/OSPL_overview.png
          :width: 200px

   * - OTT
     - ISC Bulletin
     - v1
     - `Open Folder <https://github.com/ecastillot/UTDQuake/tree/figures/figures/networks/OTT>`_
     - .. image:: https://raw.githubusercontent.com/ecastillot/UTDQuake/figures/figures/networks/OTT/OTT_overview.png
          :width: 200px

   * - PDG
     - ISC Bulletin
     - v1
     - `Open Folder <https://github.com/ecastillot/UTDQuake/tree/figures/figures/networks/PDG>`_
     - .. image:: https://raw.githubusercontent.com/ecastillot/UTDQuake/figures/figures/networks/PDG/PDG_overview.png
          :width: 200px

   * - PRE
     - ISC Bulletin
     - v1
     - `Open Folder <https://github.com/ecastillot/UTDQuake/tree/figures/figures/networks/PRE>`_
     - .. image:: https://raw.githubusercontent.com/ecastillot/UTDQuake/figures/figures/networks/PRE/PRE_overview.png
          :width: 200px

   * - RHSSO
     - ISC Bulletin
     - v1
     - `Open Folder <https://github.com/ecastillot/UTDQuake/tree/figures/figures/networks/RHSSO>`_
     - .. image:: https://raw.githubusercontent.com/ecastillot/UTDQuake/figures/figures/networks/RHSSO/RHSSO_overview.png
          :width: 200px

   * - RSNC
     - ISC Bulletin
     - v1
     - `Open Folder <https://github.com/ecastillot/UTDQuake/tree/figures/figures/networks/RSNC>`_
     - .. image:: https://raw.githubusercontent.com/ecastillot/UTDQuake/figures/figures/networks/RSNC/RSNC_overview.png
          :width: 200px

   * - RSPR
     - ISC Bulletin
     - v1
     - `Open Folder <https://github.com/ecastillot/UTDQuake/tree/figures/figures/networks/RSPR>`_
     - .. image:: https://raw.githubusercontent.com/ecastillot/UTDQuake/figures/figures/networks/RSPR/RSPR_overview.png
          :width: 200px

   * - SJA
     - ISC Bulletin
     - v1
     - `Open Folder <https://github.com/ecastillot/UTDQuake/tree/figures/figures/networks/SJA>`_
     - .. image:: https://raw.githubusercontent.com/ecastillot/UTDQuake/figures/figures/networks/SJA/SJA_overview.png
          :width: 200px

   * - TAP
     - ISC Bulletin
     - v1
     - `Open Folder <https://github.com/ecastillot/UTDQuake/tree/figures/figures/networks/TAP>`_
     - .. image:: https://raw.githubusercontent.com/ecastillot/UTDQuake/figures/figures/networks/TAP/TAP_overview.png
          :width: 200px

   * - THE
     - ISC Bulletin
     - v1
     - `Open Folder <https://github.com/ecastillot/UTDQuake/tree/figures/figures/networks/THE>`_
     - .. image:: https://raw.githubusercontent.com/ecastillot/UTDQuake/figures/figures/networks/THE/THE_overview.png
          :width: 200px

   * - TIR
     - ISC Bulletin
     - v1
     - `Open Folder <https://github.com/ecastillot/UTDQuake/tree/figures/figures/networks/TIR>`_
     - .. image:: https://raw.githubusercontent.com/ecastillot/UTDQuake/figures/figures/networks/TIR/TIR_overview.png
          :width: 200px

   * - TUN
     - ISC Bulletin
     - v1
     - `Open Folder <https://github.com/ecastillot/UTDQuake/tree/figures/figures/networks/TUN>`_
     - .. image:: https://raw.githubusercontent.com/ecastillot/UTDQuake/figures/figures/networks/TUN/TUN_overview.png
          :width: 200px

   * - UCC
     - ISC Bulletin
     - v1
     - `Open Folder <https://github.com/ecastillot/UTDQuake/tree/figures/figures/networks/UCC>`_
     - .. image:: https://raw.githubusercontent.com/ecastillot/UTDQuake/figures/figures/networks/UCC/UCC_overview.png
          :width: 200px

   * - UCR
     - ISC Bulletin
     - v1
     - `Open Folder <https://github.com/ecastillot/UTDQuake/tree/figures/figures/networks/UCR>`_
     - .. image:: https://raw.githubusercontent.com/ecastillot/UTDQuake/figures/figures/networks/UCR/UCR_overview.png
          :width: 200px

   * - UPA
     - ISC Bulletin
     - v1
     - `Open Folder <https://github.com/ecastillot/UTDQuake/tree/figures/figures/networks/UPA>`_
     - .. image:: https://raw.githubusercontent.com/ecastillot/UTDQuake/figures/figures/networks/UPA/UPA_overview.png
          :width: 200px

   * - UPP
     - ISC Bulletin
     - v1
     - `Open Folder <https://github.com/ecastillot/UTDQuake/tree/figures/figures/networks/UPP>`_
     - .. image:: https://raw.githubusercontent.com/ecastillot/UTDQuake/figures/figures/networks/UPP/UPP_overview.png
          :width: 200px

   * - USP
     - ISC Bulletin
     - v1
     - `Open Folder <https://github.com/ecastillot/UTDQuake/tree/figures/figures/networks/USP>`_
     - .. image:: https://raw.githubusercontent.com/ecastillot/UTDQuake/figures/figures/networks/USP/USP_overview.png
          :width: 200px

   * - VAO
     - ISC Bulletin
     - v1
     - `Open Folder <https://github.com/ecastillot/UTDQuake/tree/figures/figures/networks/VAO>`_
     - .. image:: https://raw.githubusercontent.com/ecastillot/UTDQuake/figures/figures/networks/VAO/VAO_overview.png
          :width: 200px

   * - VIE
     - ISC Bulletin
     - v1
     - `Open Folder <https://github.com/ecastillot/UTDQuake/tree/figures/figures/networks/VIE>`_
     - .. image:: https://raw.githubusercontent.com/ecastillot/UTDQuake/figures/figures/networks/VIE/VIE_overview.png
          :width: 200px

   * - ZUR
     - ISC Bulletin
     - v1
     - `Open Folder <https://github.com/ecastillot/UTDQuake/tree/figures/figures/networks/ZUR>`_
     - .. image:: https://raw.githubusercontent.com/ecastillot/UTDQuake/figures/figures/networks/ZUR/ZUR_overview.png
          :width: 200px

   * - CM
     - SGC
     - v2
     - `Open Folder <https://github.com/ecastillot/UTDQuake/tree/figures/figures/networks/CM>`_
     - .. image:: https://raw.githubusercontent.com/ecastillot/UTDQuake/figures/figures/networks/CM/CM_overview.png
          :width: 200px

   * - R01
     - COSEISMIQ
     - v2
     - `Open Folder <https://github.com/ecastillot/UTDQuake/tree/figures/figures/networks/R01>`_
     - .. image:: https://raw.githubusercontent.com/ecastillot/UTDQuake/figures/figures/networks/R01/R01_overview.png
          :width: 200px

   * - R02
     - Synthetic Ridgecrest 2019 catalog
     - v2
     - `Open Folder <https://github.com/ecastillot/UTDQuake/tree/figures/figures/networks/R02>`_
     - .. image:: https://raw.githubusercontent.com/ecastillot/UTDQuake/figures/figures/networks/R02/R02_overview.png
          :width: 200px

   * - R03
     - tx_highres
     - v2
     - `Open Folder <https://github.com/ecastillot/UTDQuake/tree/figures/figures/networks/R03>`_
     - .. image:: https://raw.githubusercontent.com/ecastillot/UTDQuake/figures/figures/networks/R03/R03_overview.png
          :width: 200px

   * - R04
     - The Geysers
     - v2
     - `Open Folder <https://github.com/ecastillot/UTDQuake/tree/figures/figures/networks/R04>`_
     - .. image:: https://raw.githubusercontent.com/ecastillot/UTDQuake/figures/figures/networks/R04/R04_overview.png
          :width: 200px

   * - R05
     - ToC2ME
     - v2
     - `Open Folder <https://github.com/ecastillot/UTDQuake/tree/figures/figures/networks/R05>`_
     - .. image:: https://raw.githubusercontent.com/ecastillot/UTDQuake/figures/figures/networks/R05/R05_overview.png
          :width: 200px

   * - R06
     - ESPOO
     - v2
     - `Open Folder <https://github.com/ecastillot/UTDQuake/tree/figures/figures/networks/R06>`_
     - .. image:: https://raw.githubusercontent.com/ecastillot/UTDQuake/figures/figures/networks/R06/R06_overview.png
          :width: 200px

   * - R07
     - LASSO
     - v2
     - `Open Folder <https://github.com/ecastillot/UTDQuake/tree/figures/figures/networks/R07>`_
     - .. image:: https://raw.githubusercontent.com/ecastillot/UTDQuake/figures/figures/networks/R07/R07_overview.png
          :width: 200px

   * - R08
     - ComCat events z>30km
     - v2
     - `Open Folder <https://github.com/ecastillot/UTDQuake/tree/figures/figures/networks/R08>`_
     - .. image:: https://raw.githubusercontent.com/ecastillot/UTDQuake/figures/figures/networks/R08/R08_overview.png
          :width: 200px


.. raw:: html


   </div>

.. _overview-DAS-data:
DAS Data
----------------------

.. raw:: html

   <div align="center">

.. list-table:: Available Networks
   :widths: 12 20 8 25 30
   :header-rows: 1

   * - utdq_net
     - Catalog
     - Version
     - Figures Folder
     - Preview

   * - UWF
     - University of Washington DAS catalog
     - v1
     - `Open Folder <https://github.com/ecastillot/UTDQuake/tree/figures/figures/networks_DAS/UWF>`_
     - .. image:: https://raw.githubusercontent.com/ecastillot/UTDQuake/figures/figures/networks_DAS/UWF/UWF_overview.png
          :width: 200px


.. raw:: html


   </div>
