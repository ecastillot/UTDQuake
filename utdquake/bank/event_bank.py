import obsplus
import sqlite3
import pandas as pd
import logging

logger = logging.getLogger(__name__)

class EventBank(obsplus.EventBank):
    """
    A class to manage event data, inheriting from obsplus.EventBank.
    This class can be extended with additional methods or properties as needed.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Additional initialization can be added here if needed

    def get_table_names(self):
        """
        Returns a list of table names in the event bank.
        """
        conn = sqlite3.connect(self.index_path)
        query = "SELECT name FROM sqlite_master WHERE type='table';"
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df['name'].tolist()

    def _read_table(self,query):
        """
        Returns a summary of the event bank.
        """
        conn = sqlite3.connect(self.index_path)
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    
    def get_summary(self):
        """
        Returns a summary of the event bank.
        """
        query = "SELECT * FROM '/events/summary'"
        return self._read_table(query)

    def _get_station_query(self, table_name):
        
        query = f"""
                SELECT *
                FROM "/stations/{table_name}"
                WHERE rowid IN (
                        SELECT MIN(rowid)
                        FROM "/stations/{table_name}"
                        GROUP BY network, station
                )
                """
        return query

    def get_station_summary(self, available=True):
        """
        Returns a list of stations in the event bank.
        
        Parameters:
        available (bool): If True, returns only available stations; if False, returns unavailable stations.
        
        Returns:
        pd.DataFrame: A DataFrame containing the station information.
        """
        if available:
            table_class = "gd"
        else:
            table_class = "bad"

        if f"/stations/{table_class}" not in self.get_table_names():
            logger.warning(f"Table '/stations/{table_class}' does not exist in the event bank.")
            return pd.DataFrame()

        query = self._get_station_query(table_class)
        return self._read_table(query)