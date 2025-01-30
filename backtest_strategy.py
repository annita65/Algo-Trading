import MetaTrader5 as mt5
import pandas as pd
import matplotlib.pyplot as plt

# Initialize MetaTrader 5 connection
if not mt5.initialize():
    print("Failed to initialize MT5!")
    quit()

# Define symbol and time frame for backtesting
symbol = "EURUSD"
timeframe = mt5.TIMEFRAME_M15  # 15-minute timeframe
start_date = "2023-01-01"  # Start date for historical data
end_date = "2023-12-31"  # End date for historical data

# Fetch historical data
rates = mt5.copy_rates_range(
    symbol,
    timeframe,
    pd.Timestamp(start_date).to_pydatetime(),
    pd.Timestamp(end_date).to_pydatetime()
)

if rates is None:
    print("Failed to fetch historical data")
    mt5.shutdown()
    quit()

# Convert to a pandas DataFrame
df = pd.DataFrame(rates)
df['time'] = pd.to_datetime(df['time'], unit='s')  # Convert timestamp
df.set_index('time', inplace=True)

# Calculate Moving Averages
df['SMA_10'] = df['close'].rolling(window=10).mean()
df['SMA_30'] = df['close'].rolling(window=30).mean()

# Backtesting the strategy
initial_balance = 10000  # Initial capital in USD
lot_size = 0.1  # Lot size per trade
balance = initial_balance
positions = []  # To track open positions
equity_curve = []  # To track equity over time

for i in range(30, len(df)):
    if df['SMA_10'][i] > df['SMA_30'][i] and df['SMA_10'][i - 1] <= df['SMA_30'][i - 1]:
        # Buy signal
        positions.append(df['close'][i])  # Open a buy position
        print(f"Buy Signal at {df.index[i]} - Price: {df['close'][i]}")
    elif df['SMA_10'][i] < df['SMA_30'][i] and df['SMA_10'][i - 1] >= df['SMA_30'][i - 1]:
        # Sell signal
        if positions:
            entry_price = positions.pop(0)
            profit = (df['close'][i] - entry_price) * 100000 * lot_size  # Profit calculation
            balance += profit
            print(f"Sell Signal at {df.index[i]} - Price: {df['close'][i]}, Profit: {profit:.2f}")
    equity_curve.append(balance)

# Plot the equity curve
plt.figure(figsize=(12, 6))
plt.plot(df.index[-len(equity_curve):], equity_curve, label="Equity Curve")
plt.title("Backtest Results")
plt.xlabel("Time")
plt.ylabel("Balance (USD)")
plt.legend()
plt.grid()
plt.show()

# Print summary
print(f"Initial Balance: ${initial_balance}")
print(f"Final Balance: ${balance:.2f}")
print(f"Net Profit: ${balance - initial_balance:.2f}")

# Shutdown MetaTrader connection
mt5.shutdown()
