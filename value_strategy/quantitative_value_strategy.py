import numpy as np
import pandas as pd
import xlsxwriter
import requests
from scipy import stats
import math
from statistics import mean

# Import API token from a separate module (secret.py)
from value_strategy.secret import IEX_CLOUD_API_TOKEN

def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

# Load the list of S&P 500 stocks from a CSV file
stocks = pd.read_csv('sp_500_stocks.csv')

# Define a symbol (e.g., 'AAPL') to retrieve data for
symbol = 'AAPL'

# Create the API URL for a specific stock
api_url = f'https://cloud.iexapis.com/stable/stock/{symbol}/quote?token={IEX_CLOUD_API_TOKEN}'

# Make an API request and parse the JSON response
data = requests.get(api_url).json()
price = data['latestPrice']
pe_ratio = data['peRatio']

# Split the list of stock symbols into groups of 100 symbols
symbol_groups = list(chunks(stocks['Ticker'], 100))
symbol_strings = [','.join(symbol_group) for symbol_group in symbol_groups]

# Define column names for the final DataFrame
my_columns = ['Ticker', 'Price', 'Price-to-Earnings Ratio', 'Number of Shares to Buy']

# Create an empty DataFrame with the defined columns
final_dataframe = pd.DataFrame(columns=my_columns)

# Loop through each group of symbols
for symbol_string in symbol_strings:
    # Create a batch API call URL for the symbols in the current group
    batch_api_call_url = f'https://cloud.iexapis.com/v1/stock/market/batch?symbols={symbol_string}&types=quote&token={IEX_CLOUD_API_TOKEN}'

    # Send a GET request to the API
    data = requests.get(batch_api_call_url).json()

    # Loop through each symbol in the current group
    for symbol in symbol_string.split(','):
        if symbol in data:
            # Extract relevant data for the current symbol
            new_data = pd.DataFrame(
                [[symbol,
                data[symbol]['quote']['latestPrice'],
                data[symbol]['quote']['peRatio'],
                'N/A']],
                columns=my_columns
            )
            final_dataframe = pd.concat([final_dataframe, new_data], ignore_index=True)
        else:
            print(f"Symbol '{symbol}' not found in data.")

# Sort the DataFrame by the 'Price-to-Earnings Ratio' column in descending order
final_dataframe.sort_values('Price-to-Earnings Ratio', ascending=False, inplace=True)

# Filter out stocks with a Price-to-Earnings Ratio less than or equal to 0
final_dataframe = final_dataframe[final_dataframe['Price-to-Earnings Ratio'] > 0]

# Select the top 50 stocks with the highest Price-to-Earnings Ratio
final_dataframe = final_dataframe[:50]

# Reset the index and drop the old index column
final_dataframe.reset_index(inplace=True, drop=True)

def portfolio_input():
    global portfolio_size
    portfolio_size = input("Enter the value of your portfolio:")

    try:
        val = float(portfolio_size)
    except ValueError:
        print("That's not a number! Try again.")
        portfolio_input()

# Get user input for portfolio size
portfolio_input()
print('Portfolio Size:', portfolio_size)

# Calculate the position size for each stock in the portfolio
position_size = float(portfolio_size) / len(final_dataframe.index)

# Loop through each stock in the final_dataframe
for row in final_dataframe.index:
    # Calculate the number of shares to buy for each stock
    final_dataframe.loc[row, 'Number of Shares to Buy'] = math.floor(position_size / final_dataframe.loc[row, 'Price'])

# Define a symbol (e.g., 'AAPL') to retrieve additional financial metrics
symbol = 'AAPL'

# Create a batch API call URL to get more metrics for the specified symbol
batch_api_call_url = f'https://cloud.iexapis.com/v1/stock/market/batch?symbols={symbol}&types=quote,advanced-stats&token={IEX_CLOUD_API_TOKEN}'

# Send a GET request to the API and parse the JSON response
data = requests.get(batch_api_call_url).json()

# Extract the required financial metrics from the JSON response
pe_ratio = data[symbol]['quote']['peRatio']
pb_ratio = data[symbol]['advanced-stats']['priceToBook']
ps_ratio = data[symbol]['advanced-stats']['priceToSales']

# Calculate enterprise value and related metrics manually
enterprise_value = data[symbol]['advanced-stats']['enterpriseValue']
ebitda = data[symbol]['advanced-stats']['EBITDA']
ev_to_ebitda = enterprise_value / ebitda

gross_profit = data[symbol]['advanced-stats']['grossProfit']
ev_to_gross_profit = enterprise_value / gross_profit

# Define column names for the resulting DataFrame
rv_columns = [
    'Ticker',
    'Price',
    'Number of Shares to Buy',
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
                'N/A',  # Placeholder for 'Number of Shares to Buy'
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

# Iterate through a list of NUMERIC columns in the DataFrame
numeric_columns = ['Price-to-Earnings Ratio', 'Price-to-Book Ratio', 'Price-to-Sales Ratio', 'EV/EBITDA', 'EV/GP']
for column in numeric_columns:
    # Fill missing values (NaN) in the specified column with the mean of that column
    rv_dataframe[column].fillna(rv_dataframe[column].mean(), inplace=True)

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

# Print the resulting DataFrame
print(rv_dataframe)
