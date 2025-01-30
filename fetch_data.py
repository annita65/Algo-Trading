import MetaTrader5 as mt5
import pandas as pd

# Initialize MetaTrader 5 connection
if not mt5.initialize():
    print("Failed to initialize MT5!")
    quit()

# Log in to your trading account (already logged in via the MT5 platform)
account_info = mt5.account_info()
if account_info is None:
    print("Failed to retrieve account info")
    mt5.shutdown()
    quit()

print(f"Connected to account: {account_info.login}")

# Define the symbol to trade (e.g., EURUSD)
symbol = "EURUSD"
if not mt5.symbol_select(symbol, True):
    print(f"Failed to select symbol {symbol}")
    mt5.shutdown()
    quit()

# Fetch live data (last 100 candlesticks, 1-minute timeframe)
rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, 100)
df = pd.DataFrame(rates)
df['time'] = pd.to_datetime(df['time'], unit='s')  # Convert timestamps

# Display the data
print(df[['time', 'open', 'high', 'low', 'close']])

# Shutdown MetaTrader connection
mt5.shutdown()
