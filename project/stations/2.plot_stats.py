import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

def plot_network_histogram(df, output_path='network_histogram.png', dpi=300, top=20):
    """
    Plots a histogram of the top N networks in the 'network' column and saves it.

    Parameters
    ----------
    df : pandas.DataFrame
        The DataFrame containing a 'network' column.
    output_path : str, optional
        File path to save the histogram image.
    dpi : int, optional
        Dots per inch for the saved figure.
    top : int, optional
        Number of top networks to show based on frequency.
    """
    # Get top N networks
    top_networks = df['network'].value_counts().nlargest(top).index
    df_top = df[df['network'].isin(top_networks)]

    plt.figure(figsize=(10, 6))
    sns.countplot(data=df_top, x='network',
                  order=df_top['network'].value_counts().index,
                  palette='viridis')
    plt.title(f'Histogram of Top {top} Networks')
    plt.xlabel('Network')
    plt.ylabel('Count')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(output_path, dpi=dpi)
    plt.close()

#stations

path = "/groups/igonin/PHASED/stations/.stations.db"
conn = sqlite3.connect(path)
query = "SELECT name FROM sqlite_master WHERE type='table';"
tables = pd.read_sql_query(query, conn)
print(tables)

df = pd.read_sql_query('SELECT * FROM "stations_index"', conn)
df["location"] = df["location"].astype(str).str.zfill(2)
df = df.drop_duplicates(subset=['network', 'station', 'location', 'channel'])
print(df)
print(df.columns.tolist())

output_path = "/groups/igonin/ecastillo/UTDQuake/project/stations/network_stats.png"
plot_network_histogram(df,output_path=output_path)