def get_most_undervalued_stock():

    import numpy as np
    import pandas as pd
    import xlsxwriter
    import requests
    from scipy import stats
    import math
    from statistics import mean



    def chunks(lst, n):
        """Yield successive n-sized chunks from lst."""
        for i in range(0, len(lst), n):
            yield lst[i:i + n]

    # Open the file for reading
    with open('tickers.py', 'r') as file:
    # Read the file content
        stocks = file.read()

# Now, the variable 'tickers' contains the content of the file
# You may want to split it into a list of tickers
    stocks = stocks.split(',')


    # Split the list of stock symbols into groups of 100 symbols
    symbol_groups = list(chunks(stocks['Ticker'], 100))
    symbol_strings = [','.join(symbol_group) for symbol_group in symbol_groups]

    # Define column names for the resulting DataFrame
    rv_columns = [
        'Ticker',
        'Price',
        'Price-to-Earnings Ratio',
        'PE Percentile',
        'Price-to-Book Ratio',
        'PB Percentile',
        'Price-to-Sales Ratio',
        'PS Percentile',
        'EV/EBITDA',
        'EV/EBITDA Percentile',
        'EV/GP',
        'EV/GP Percentile',
        'RV Score'
    ]

    # Create an empty DataFrame with the defined columns
    rv_dataframe = pd.DataFrame(columns=rv_columns)

    # Loop through each symbol string in the list of symbol_strings
    for symbol_string in symbol_strings:
        # Create the API URL for batch requests
        batch_api_call_url = f'https://cloud.iexapis.com/v1/stock/market/batch?symbols={symbol_string}&types=quote,advanced-stats&token={IEX_CLOUD_API_TOKEN}'
        
        # Send a GET request to the API and parse the JSON response
        data = requests.get(batch_api_call_url).json()

        # Loop through each symbol in the symbol_string
        for symbol in symbol_string.split(','):
            # Check if the symbol is found in the data
            if symbol in data:
                # Extract relevant data from the JSON response
                enterprise_value = data[symbol]['advanced-stats']['enterpriseValue']
                ebitda = data[symbol]['advanced-stats']['EBITDA']
                gross_profit = data[symbol]['advanced-stats']['grossProfit']
            else:
                # Print a message if the symbol is not found in the data and continue to the next symbol
                print(f"Symbol '{symbol}' not found in data.")
                continue
            
            # Calculate the EV/EBITDA ratio, handling cases where ebitda is None or 0
            try:
                ev_to_ebitda = enterprise_value / ebitda
            except TypeError:
                ev_to_ebitda = np.NaN
            
            # Calculate the EV/GP ratio, handling cases where gross_profit is None or 0
            try:
                ev_to_gross_profit = enterprise_value / gross_profit
            except TypeError:
                ev_to_gross_profit = np.NaN

            # Check if the symbol is found in the data (again)
            if symbol in data:
                # Create a new DataFrame with the extracted data for the current symbol
                new_data = pd.DataFrame(
                    [[symbol,
                    data[symbol]['quote']['latestPrice'],
                    data[symbol]['quote']['peRatio'],
                    'N/A',  # Placeholder for 'PE Percentile'
                    data[symbol]['advanced-stats']['priceToBook'],
                    'N/A',  # Placeholder for 'PB Percentile'
                    data[symbol]['advanced-stats']['priceToSales'],
                    'N/A',  # Placeholder for 'PS Percentile'
                    ev_to_ebitda,
                    'N/A',  # Placeholder for 'EV/EBITDA Percentile'
                    ev_to_gross_profit,
                    'N/A',  # Placeholder for 'EV/GP Percentile'
                    'N/A'   # Placeholder for 'RV Score'
                    ]], 
                    columns=rv_columns
                )
                
                # Concatenate the new DataFrame to the rv_dataframe
                rv_dataframe = pd.concat([rv_dataframe, new_data], ignore_index=True)
            else:
                # Continue to the next symbol if it's not found in the data
                continue

    # Check for rows with missing values (NaN) in the DataFrame
    missing_data = rv_dataframe[rv_dataframe.isnull().any(axis=1)]

    # Import the `percentileofscore` function from the `scipy.stats` module
    from scipy.stats import percentileofscore as score

    # Create a dictionary that maps specific metrics to their corresponding percentile columns
    metrics = {
        'Price-to-Earnings Ratio': 'PE Percentile',
        'Price-to-Book Ratio': 'PB Percentile',
        'Price-to-Sales Ratio': 'PS Percentile',
        'EV/EBITDA': 'EV/EBITDA Percentile',
        'EV/GP': 'EV/GP Percentile'
    }

    # Loop through each metric in the dictionary
    for metric in metrics.keys():
        # Loop through each row in the DataFrame
        for row in rv_dataframe.index:
            # Calculate the percentile for the specific metric in the current row
            percentile = score(rv_dataframe[metric], rv_dataframe.loc[row, metric])
            # Assign the calculated percentile to the corresponding percentile column in the DataFrame
            rv_dataframe.loc[row, metrics[metric]] = percentile / 100

    # Import the `mean` function from the `statistics` module
    from statistics import mean

    # Loop through each row in the DataFrame
    for row in rv_dataframe.index:
        # Create an empty list to store percentile values for each metric
        value_percentiles = []
        
        # Loop through each metric in the metrics dictionary
        for metric in metrics.keys():
            # Append the percentile value for the current metric to the list
            value_percentiles.append(rv_dataframe.loc[row, metrics[metric]])
        
        # Calculate the mean (average) of the percentile values for all metrics and assign it to the 'RV Score' column
        rv_dataframe.loc[row, 'RV Score'] = mean(value_percentiles)

    # Sort the DataFrame by the 'RV Score' column in ascending order (lower scores first)
    rv_dataframe.sort_values('RV Score', ascending=True, inplace=True)

    # Select the top 50 rows (stocks) with the lowest RV Scores
    rv_dataframe = rv_dataframe[:50]

    # Reset the index of the DataFrame to start from 0 and drop the old index
    rv_dataframe.reset_index(drop=True, inplace=True)



    
    # Get the 0th row (first row) from the DataFrame
    first_row = rv_dataframe.iloc[0]

    # Access the 'Ticker' and 'RV Score' columns for the first row
    ticker = first_row['Ticker']

    # Return the 'Ticker' and 'RV Score' for the first row
    return ticker


get_most_undervalued_stock()