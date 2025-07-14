if __name__   == "__main__":
    import glob
    import os
    import obsplus
    from obspy import read_events
    # Example usage
    # test_path = "/groups/igonin/Bank/events/uu"
    # xml_files = glob.glob(os.path.join(test_path, "**","*.xml"),recursive=True)
    # len_xml_files = len(xml_files)
    # print(f"Found {len_xml_files} XML files in {test_path}")

    cat = read_events("/groups/igonin/Bank/events/tx/2024/01/01/texnet2024aaaa.xml")
    df = cat.to_df()
    arrivals = cat.arrivals_to_df()
    picks = cat.picks_to_df()
    print(arrivals)
    print(picks)
    # print(df.info())
    # print(df[["event_id"]].head())