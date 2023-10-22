import pandas as pd
import requests
import math
from scipy import stats
from statistics import mean

# Load the list of S&P 500 stocks
stocks = pd.read_csv('sp_500_stocks.csv')

# Define your IEX Cloud API token
from secrets import IEX_CLOUD_API_TOKEN

# Define necessary columns for the final DataFrame
my_columns = ['Ticker', 'Price', 'One-Year Price Return', 'Number of Shares to Buy']

# Initialize the final DataFrame
final_dataframe = pd.DataFrame(columns=my_columns)

# Split the stock symbols into batches of 100
symbol_groups = [stocks['Ticker'][i:i + 100] for i in range(0, len(stocks), 100)]

# Create a new DataFrame with stock information
for symbol_group in symbol_groups:
    symbol_string = ','.join(symbol_group)
    batch_api_call_url = f'https://sandbox.iexapis.com/stable/stock/market/batch/?types=stats,quote&symbols={symbol_string}&token={IEX_CLOUD_API_TOKEN}'
    data = requests.get(batch_api_call_url).json()
    for symbol in symbol_group:
        final_dataframe = final_dataframe.append(
            pd.Series([symbol,
                       data[symbol]['quote']['latestPrice'],
                       data[symbol]['stats']['year1ChangePercent'],
                       'N/A'], index=my_columns),
            ignore_index=True
        )

# Calculate the number of shares to buy based on your portfolio size
def portfolio_input():
    global portfolio_size
    portfolio_size = input("Enter the value of your portfolio: ")
    try:
        portfolio_size = float(portfolio_size)
    except ValueError:
        print("Please enter a valid number.")
        portfolio_input()

portfolio_input()

position_size = portfolio_size / len(final_dataframe)
final_dataframe['Number of Shares to Buy'] = final_dataframe.apply(
    lambda row: math.floor(position_size / row['Price']), axis=1
)

# Calculate the percentile ranks for one-year price returns
final_dataframe['One-Year Return Percentile'] = final_dataframe['One-Year Price Return'].apply(
    lambda x: stats.percentileofscore(final_dataframe['One-Year Price Return'], x) / 100
)

# Calculate the HQM (High-Quality Momentum) Score
time_periods = ['One-Year']
for row in final_dataframe.index:
    momentum_percentiles = [final_dataframe.loc[row, f'{time_period} Return Percentile'] for time_period in time_periods]
    final_dataframe.loc[row, 'HQM Score'] = mean(momentum_percentiles)

# Sort the DataFrame by HQM Score and select the top 50 stocks
hqm_dataframe = final_dataframe.sort_values(by='HQM Score', ascending=False)[:50]

# Print or save the top 50 momentum stocks
print(hqm_dataframe)


# Save the top 50 momentum stocks to a CSV file
hqm_dataframe.to_csv('top_momentum_stocks.csv', index=False)
