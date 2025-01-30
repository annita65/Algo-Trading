import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime

# Initialize MT5 connection
if not mt5.initialize():
    print("Failed to initialize MT5!")
    quit()

# Login to your account (optional, if not already logged in)
account_number = 5033135195  # Replace with your demo account number
password = "*7NbBeMi"  # Replace with your account password
server = "MetaQuotes-Demo"  # Replace with your broker's demo server name
if not mt5.login(account_number, password, server):
    print(f"Failed to login to account {account_number}. Error: {mt5.last_error()}")
    mt5.shutdown()
    quit()

# Fetch historical data for EURUSD
symbol = "EURUSD"  # Replace with your broker's exact symbol name
timeframe = mt5.TIMEFRAME_M1  # 1-minute timeframe
rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, 10)  # Fetch last 10 candles

if rates is None:
    print(f"Failed to fetch data for {symbol}. Error: {mt5.last_error()}")
else:
    # Convert data to DataFrame and print
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    print(df)

# Shutdown connection
mt5.shutdown()
