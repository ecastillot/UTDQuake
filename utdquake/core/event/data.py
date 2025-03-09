import pandas as pd
import copy


def proc_data(data, required_columns, date_columns=None):
    """
    Process the input DataFrame by validating columns, removing duplicates, 
    and optionally parsing date information.

    Parameters:
        data (pd.DataFrame): Input DataFrame containing data to process.
        required_columns (list): List of mandatory columns that must be present in the DataFrame.
        date_columns (list, optional): List of columns to be parsed as datetime. Defaults to None.
        

    Returns:
        pd.DataFrame: Processed DataFrame.
    
    Raises:
        Exception: If required columns are missing, if data is empty, 
                   or if invalid parameters are provided.
    """
    # Error message for missing required columns
    msg = {"required_columns": "The mandatory columns are missing in the data object. "
                               + f"Required columns: {required_columns}"}
    # Check if all mandatory columns are present in the DataFrame
    if not all(item in data.columns for item in required_columns):
        raise Exception(msg["required_columns"])

    # Remove duplicate rows based on the required columns
    # data.drop_duplicates(subset=required_columns, ignore_index=True, inplace=True)
    data.drop_duplicates(subset=required_columns, ignore_index=False, inplace=True)

    # Check if the DataFrame is empty after removing duplicates
    if data.empty:
        raise Exception("The data object is empty.")

    # Parse date columns, if specified
    if date_columns is not None:
        if not isinstance(date_columns, list):
            raise Exception("The 'date_columns' parameter must be a list.")
        for col_date in date_columns:
            if col_date in data.columns:
                data[col_date] = pd.to_datetime(
                    data[col_date], errors="coerce"
                ).dt.tz_localize(None)

    return data


class DataFrameHelper:
    """
    A subclass of pandas DataFrame to handle data with additional functionalities.

    Attributes:
        data (pd.DataFrame): The processed DataFrame containing data.
        required_columns (list): List of mandatory columns in the DataFrame.
        date_columns (list, optional): List of columns to parse as datetime.
    """

    def __init__(self, data, required_columns, date_columns=None, author=None):
        """
        Initialize the DataFrameHelper instance.

        Parameters:
            data (pd.DataFrame): Input DataFrame containing earthquake data.
            required_columns (list): List of mandatory columns in the DataFrame.
            date_columns (list, optional): List of columns to parse as datetime. Defaults to None.
            author (str, optional): The author or source of the picks data.
                
        """
        self.data = proc_data(
            data=data, 
            required_columns=required_columns,
            date_columns=date_columns, 
        )

        # Store custom attributes
        self.author = author
        self.required_columns = required_columns
        self.date_columns = date_columns

    @property
    def empty(self):
        """Check if the DataFrame is empty."""
        return self.data.empty

    def __len__(self):
        """Return the number of rows in the DataFrame."""
        return len(self.data)

    def __getitem__(self, key):
        return self.data[key]
    
    def __setitem__(self, key, value):
        self.data[key] = value

    def __str__(self, extended=False):
        """
        Return a string representation of the DataFrameHelper instance.

        Parameters:
            extended (bool): If True, return the full DataFrame as a string. Defaults to False.

        Returns:
            str: String representation of the DataFrameHelper.
        """
        if extended:
            msg = self.data.__str__()
        else:
            msg = f"DataFrameHelper ({self.__len__()} rows)"
            # msg += "\n-" * len(msg)
        return msg

    def sample(self, n=1):
        """
        Return a random sample of rows from the DataFrame.

        Parameters:
            n (int, optional): Number of rows to sample. Defaults to 10.

        Returns:
            pd.DataFrame: Sampled DataFrame.
        """
        self.data = self.data.sample(n)
        return self

    def append(self, data):
        """
        Append new data to the DataFrameHelper.

        Parameters:
            data (pd.DataFrame): DataFrame to append.

        Returns:
            DataFrameHelper: Updated DataFrameHelper instance.
        
        Raises:
            TypeError: If the input data is not a DataFrame.
        """
        if isinstance(data, pd.DataFrame):
            data = proc_data(
                data, 
                required_columns=self.required_columns,
                date_columns=self.date_columns,
            )
            self.data = pd.concat([self.data, data])
        else:
            msg = 'Append only supports a single DataFrame object as an argument.'
            raise TypeError(msg)
        return self

    def remove_data(self, rowval):
        """
        Remove rows from the data based on specified conditions.

        Parameters:
            rowval (dict): Dictionary where keys are column names and values are lists of values to remove.

        Returns:
            DataFrameHelper: Updated DataFrameHelper instance.
        
        Raises:
            Exception: If `rowval` is not a dictionary.
        """
        if not isinstance(rowval, dict):
            raise Exception("rowval must be a dictionary")
        
        mask = self.data.isin(rowval)
        mask = mask.any(axis='columns')
        self.data = self.data[~mask]
        # self.data.reset_index(drop=True, inplace=True)
        return self
    
    def dropna(self, subset=None):
        """
        Remove rows with missing values from the DataFrame.

        Parameters:
            subset (list, optional): List of columns to consider when dropping rows. Defaults to None.

        Returns:
            DataFrameHelper: Updated DataFrameHelper instance.
        """
        self.data = self.data.dropna(subset=subset)
        # self.data.reset_index(drop=True, inplace=True)
        return self
    
    def select_data(self, rowval):
        """
        Select rows in the data based on specified criteria.

        Parameters:
        -----------
        rowval : dict
            A dictionary specifying the columns and the values to select.
            Keys represent column names, and values are lists of values to filter by.

        Returns:
        --------
        self : DataFrameHelper
            The updated DataFrameHelper with only the selected rows.
        """
        if not isinstance(rowval, dict):
            raise Exception("rowval must be a dictionary")

        if self.empty:
            return self

        # Create a mask based on the specified selection criteria
        mask = self.data.isin(rowval).any(axis="columns")
        self.data = self.data[mask]
        # self.data.reset_index(drop=True, inplace=True)
        return self

    def copy(self):
        """
        Create a deep copy of the DataFrameHelper instance.

        Returns:
        --------
        DataFrameHelper
            A deep copy of the current instance.
        """
        return copy.deepcopy(self)
    
    def sort_values(self, **args):
        """
        Sort the DataFrame by the specified columns.

        Parameters:
        -----------
        args : dict
            Arguments passed to `pd.DataFrame.sort_values`.

        Returns:
        --------
        self : DataFrameHelper
            The updated DataFrameHelper instance with sorted data.
        """
        self.data = self.data.sort_values(**args)
        # self.data.reset_index(drop=True, inplace=True)
        return self

    def filter(self, key, start=None, end=None):
        """
        Filter data in the catalog based on a range of values for a specified column.

        Parameters:
        -----------
        key : str
            Name of the column to filter.
        start : int, float, or datetime.datetime, optional
            The minimum value for the filter range. Must match the data type of `data[key]`.
        end : int, float, or datetime.datetime, optional
            The maximum value for the filter range. Must match the data type of `data[key]`.

        Returns:
        --------
        self : DataFrameHelper
            The updated DataFrameHelper instance with filtered rows.
        """
        if (start is not None) and (len(self) != 0):
            self.data = self.data[self.data[key] >= start]
        
        if (end is not None) and (len(self) != 0):
            self.data = self.data[self.data[key] <= end]
        
        # self.data.reset_index(drop=True, inplace=True)
        return self