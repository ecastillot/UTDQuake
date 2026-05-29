import numpy as np
from obspy import Catalog
from .config import PICK_QC_DEFAULTS, EVENT_QC_DEFAULTS
from .picks import basic_picks_qc
from .events import events_qc
from .log import QCLog

def apply_utdq_qc(cat, debug=True, inplace=False):
    """
    Apply UTDQuake pick-level and event-level QC to a catalog.

    Wrapper around :func:`apply_utdquake_qc_to_catalog` for convenience.

    Parameters
    ----------
    cat : obspy.core.event.Catalog
        ObsPy Catalog to filter.
    debug : bool, default True
        Enable verbose output during all QC steps.
    inplace : bool, default False
        If True, modify the catalog in place. Otherwise, return a
        new filtered catalog.

    Returns
    -------
    obspy.core.event.Catalog or None
        - If `inplace=False`, returns a new filtered catalog.
        - If `inplace=True`, updates the catalog in place and returns None.

    See Also
    --------
    :func:`~utdquake.core.qc.apply_utdquake_qc_to_catalog` : Full QC workflow function.
    :data:`~utdquake.core.qc.PICK_QC_DEFAULTS` : Default pick QC parameters.
    :data:`~utdquake.core.qc.EVENT_QC_DEFAULTS` : Default event QC parameters.
    """
    filtered_cat = apply_utdquake_qc_to_catalog(cat, debug=debug)

    if inplace:
        # Replace events, origins, arrivals, and picks
        cat.events = filtered_cat.events
        return None
    else:
        return filtered_cat


def apply_utdquake_qc_to_catalog(cat,pick_qc_args=None,
                                 event_qc_args=None, 
                                 debug=False):
    """
    Apply UTDQuake pick-level and event-level QC sequentially
    to an ObsPy Catalog.

    The workflow is:

    1. Convert picks to DataFrame
    2. Apply pick-level QC via :func:`picks_qc`
    3. Filter catalog picks and arrivals using :func:`apply_picks_qc_to_catalog`
    4. Convert events to DataFrame
    5. Apply event-level QC via :func:`events_qc`
    6. Filter catalog events using :func:`apply_events_qc_to_catalog`

    Parameters
    ----------
    cat : obspy.core.event.Catalog
        Input ObsPy Catalog containing events, origins, arrivals,
        and picks.

    pick_qc_args : dict, optional
        Dictionary of keyword arguments passed to :func:`picks_qc`.

        If None, UTDQuake defaults defined in :data:`PICK_QC_DEFAULTS` are used.

        Users may provide a partial dictionary to override specific parameters.

        See Also
        --------
        picks_qc : Full list of available pick QC parameters.

    event_qc_args : dict, optional
        Dictionary of keyword arguments passed to :func:`events_qc`.

        If None, UTDQuake defaults defined in :data:`EVENT_QC_DEFAULTS` are used.

        Users may provide a partial dictionary to override specific parameters.

        See Also
        --------
        events_qc : Full list of available event QC parameters.

    debug : bool, default False
        If True, enables verbose output during all QC stages.
        This flag is also propagated to the underlying QC functions
        unless explicitly overridden in the argument dictionaries.

    Returns
    -------
    obspy.core.event.Catalog
        Catalog filtered according to both pick-level and
        event-level QC criteria.

    Notes
    -----
    - **Pick-level QC is always applied first.** Events are not filtered
      until picks have been QCed, so event-level QC operates on a catalog
      already filtered at the pick level.
    - Default QC parameter constants (:data:`PICK_QC_DEFAULTS` and
      :data:`EVENT_QC_DEFAULTS`) can be inspected or modified by advanced users.
    - Users can override any parameter in the defaults by providing a
      dictionary to ``pick_qc_args`` or ``event_qc_args``.
    
    """
    # ---------------------------------------------------------------------
    # Default pick QC parameters
    # ---------------------------------------------------------------------
    # Pick-level QC
    pick_args = PICK_QC_DEFAULTS.copy()
    if pick_qc_args:
        pick_args.update(pick_qc_args)
    pick_args["debug"] = debug
    pick_args["log"] = QCLog()

    # ---------------------------------------------------------------------
    # Default event QC parameters
    # ---------------------------------------------------------------------
    # Event-level QC
    event_args = EVENT_QC_DEFAULTS.copy()
    if event_qc_args:
        event_args.update(event_qc_args)
    event_args["debug"] = debug
    event_args["log"] = QCLog()
    
    # ---------------------------------------------------------------------
    # Pick-level QC
    # ---------------------------------------------------------------------
    picks = cat.utdq_picks_to_df()

    if debug:
        ini_picks_len = len(picks)
        print("\n#### Starting pick-level QC ####")
        print(f"Initial catalog: {ini_picks_len} picks")
        print("Parameters:", pick_args, "\n")

    picks, picks_log = basic_picks_qc(picks, **pick_args)
    pick_args["log"] = picks_log  # Update log with results from picks_qc
    cat = apply_picks_qc_to_catalog(cat, picks, debug=debug)
    
    if debug:
        print("#### Pick-level QC complete ####")

    # ---------------------------------------------------------------------
    # Event-level QC
    # ---------------------------------------------------------------------
    events = cat.utdq_events_to_df()
    if debug:
        ini_events_len = len(events)
        print("\n#### Starting event-level QC ####")
        print(f"Initial catalog: {ini_events_len } events")
        print("Parameters:", event_args, "\n")

    events, events_log = events_qc(events, **event_args)
    event_args["log"] = events_log  # Update log with results from events_qc
    cat = apply_events_qc_to_catalog(cat, events, debug=debug)

    if debug:
        print("#### Event-level QC complete ####")

    return cat


def apply_picks_qc_to_catalog(cat: Catalog, df_qc, debug=False) -> Catalog:
    """
    Apply QC from a picks DataFrame to an ObsPy Catalog.

    Keeps only Arrivals and Picks corresponding to the QCed picks.

    Parameters
    ----------
    cat : obspy.Catalog
        Input ObsPy Catalog with events, origins, arrivals, and picks.
    df_qc : pandas.DataFrame
        QCed picks DataFrame (output of `qc_picks`).
        Must contain columns 'pick_id' and 'resource_id'.
    debug : bool, default False
        If True, prints summary of removals per event and final QC totals.

    Returns
    -------
    obspy.Catalog
        Catalog with arrivals and picks filtered by QC.
    """

    # --- Sets of IDs to keep ---
    pick_ids_to_keep = set(df_qc["pick_id"].astype(str).values)
    arrival_ids_to_keep = set(df_qc["resource_id"].astype(str).values)

    total_arrivals = sum(len(event.preferred_origin().arrivals) 
                         for event in cat if event.preferred_origin())
    total_picks = sum(len(event.picks) if hasattr(event, "picks") else 0 for event in cat)

    removed_arrivals_cum = 0
    removed_picks_cum = 0

    if debug:
        print(f"QC start: {total_arrivals} arrivals, {total_picks} picks in catalog.")

    # --- Loop over events ---
    for event in cat:
        origin = event.preferred_origin()
        if not origin:
            continue

        # Filter arrivals
        kept_arrivals = [arr for arr in origin.arrivals if str(arr.resource_id) in arrival_ids_to_keep]
        removed_arrivals = len(origin.arrivals) - len(kept_arrivals)
        origin.arrivals = kept_arrivals
        removed_arrivals_cum += removed_arrivals

        if debug and removed_arrivals > 0:
            print(f"Event {event.resource_id}: removed {removed_arrivals} arrivals.")

        # Filter picks
        if hasattr(event, "picks") and event.picks:
            kept_picks = [p for p in event.picks if str(p.resource_id) in pick_ids_to_keep]
            removed_picks = len(event.picks) - len(kept_picks)
            event.picks = kept_picks
            removed_picks_cum += removed_picks

            if debug and removed_picks > 0:
                print(f"Event {event.resource_id}: removed {removed_picks} picks.")

    # --- Final QC summary ---
    if debug:
        print(
            f"Final Summary:"
            f"QC completed: removed {removed_arrivals_cum}/{total_arrivals} arrivals, "
            f"{removed_picks_cum}/{total_picks} picks. "
            f"Remaining: {total_arrivals - removed_arrivals_cum} arrivals, "
            f"{total_picks - removed_picks_cum} picks."
        )

    return cat


def apply_events_qc_to_catalog(cat: Catalog, df_qc, debug=False) -> Catalog:
    """
    Apply QC from an events DataFrame to an ObsPy Catalog.

    Keeps only events whose event_id exists in the QCed DataFrame.

    Parameters
    ----------
    cat : obspy.Catalog
        Input ObsPy Catalog.
    df_qc : pandas.DataFrame
        QCed events DataFrame (output of `events_qc`).
        Must contain column 'event_id'.
    debug : bool, default False
        If True, prints summary of removals.

    Returns
    -------
    obspy.Catalog
        Catalog filtered by event-level QC.
    """

    # --- IDs to keep ---
    event_ids_to_keep = set(df_qc["event_id"].astype(str).values)

    total_events = len(cat)
    removed_events = 0

    if debug:
        print(f"QC start: {total_events} events in catalog.")

    filtered_events = []

    for event in cat:
        event_id = str(event.resource_id)

        if event_id in event_ids_to_keep:
            filtered_events.append(event)
        else:
            removed_events += 1
            if debug:
                print(f"\tRemoved event {event_id}")

    new_catalog = Catalog(events=filtered_events)

    if debug:
        print(
            f"Final Summary:"
            f"QC completed: removed {removed_events}/{total_events} events "
            f"({(removed_events / total_events * 100):.2f}%). "
            f"Remaining: {len(new_catalog)} events."
        )

    return new_catalog


