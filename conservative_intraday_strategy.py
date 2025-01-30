import MetaTrader5 as mt5
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from ta.momentum import RSIIndicator

# Initialize MetaTrader 5 connection
if not mt5.initialize():
    print("Failed to initialize MT5!")
    quit()

# Define symbol and timeframe
symbol = "EURUSD"  # Replace with a symbol available on your broker
timeframe = mt5.TIMEFRAME_D1  # 1-week timeframe

# Define the day for intraday trading (today by default)
today = datetime.now().date()
start_time = datetime(2024, 1, 14, 8, 0)  # Start from January 13, 2025 earlier at 8:00 AM UTC
end_time = datetime(2025, 1, 17, 17, 0)  # End at January 17, 2025 at 5:00 PM UTC

# Debugging: Fetch historical data for intraday trading
print(f"Fetching 1-minute historical data for {symbol} from {start_time} to {end_time}...")
rates = mt5.copy_rates_range(symbol, timeframe, start_time, end_time)

# Handle cases where data is insufficient
if rates is None or len(rates) == 0:
    print(f"No data fetched for {symbol} on timeframe {timeframe}. Rows fetched: {0 if rates is None else len(rates)}")
    mt5.shutdown()
    quit()
else:
    print(f"Data fetched successfully! Number of rows: {len(rates)}")

# Convert to pandas DataFrame
df = pd.DataFrame(rates)
df['time'] = pd.to_datetime(df['time'], unit='s')  # Convert timestamp
df.set_index('time', inplace=True)

# Debugging: Print the first few rows of the data
print(f"Sample data:\n{df.head()}")

# Fetch higher timeframe (H1) data for trend filtering
h1_start_time = start_time - timedelta(days=1)  # Start 1 day earlier for H1 data
print(f"Fetching 1-hour historical data for trend filtering from {h1_start_time} to {end_time}...")
h1_rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_H1, h1_start_time, end_time)

# Handle cases where higher timeframe data is insufficient
if h1_rates is None or len(h1_rates) == 0:
    print(f"No H1 data fetched for {symbol}. Rows fetched: {0 if h1_rates is None else len(h1_rates)}")
    mt5.shutdown()
    quit()
else:
    print(f"H1 data fetched successfully! Number of rows: {len(h1_rates)}")

h1_df = pd.DataFrame(h1_rates)
h1_df['time'] = pd.to_datetime(h1_df['time'], unit='s')
h1_df.set_index('time', inplace=True)
h1_df['SMA_200'] = h1_df['close'].rolling(window=200).mean()

# Debugging: Print the first few rows of the H1 data
print(f"Sample H1 data:\n{h1_df.head()}")

# Calculate RSI for the main dataframe
df['RSI'] = RSIIndicator(close=df['close'], window=14).rsi()

# Define trading parameters
initial_balance = 10000  # Initial capital in USD
balance = initial_balance
lot_size = 0.1  # Fixed lot size per trade
positions = []  # Track open positions
equity_curve = []  # Track balance over time
cooldown_period = timedelta(minutes=15)  # Cooldown between trades
last_trade_time = None  # Track the time of the last trade

# Conservative stop-loss and take-profit percentages
stop_loss_percent = 1 / 100  # 1% of the entry price
take_profit_percent = 3 / 100  # 3% of the entry price

# Backtest intraday strategy
for i in range(14, len(df)):
    # Ensure cooldown period is respected
    if last_trade_time is not None and (df.index[i] - last_trade_time) < cooldown_period:
        equity_curve.append(balance)
        continue

    # Higher timeframe trend confirmation
    higher_trend = h1_df['SMA_200'].iloc[-1]
    current_price = df['close'][i]

    # Buy condition
    if df['RSI'][i] > 40 and df['RSI'][i] < 60 and current_price > higher_trend:
        entry_price = current_price
        stop_loss = entry_price * (1 - stop_loss_percent)
        take_profit = entry_price * (1 + take_profit_percent)
        positions.append((entry_price, stop_loss, take_profit, "buy"))
        last_trade_time = df.index[i]
        print(f"Buy Signal at {df.index[i]} - Entry: {entry_price:.4f}, SL: {stop_loss:.4f}, TP: {take_profit:.4f}")

    # Sell condition
    elif df['RSI'][i] > 40 and df['RSI'][i] < 60 and current_price < higher_trend:
        entry_price = current_price
        stop_loss = entry_price * (1 + stop_loss_percent)
        take_profit = entry_price * (1 - take_profit_percent)
        positions.append((entry_price, stop_loss, take_profit, "sell"))
        last_trade_time = df.index[i]
        print(f"Sell Signal at {df.index[i]} - Entry: {entry_price:.4f}, SL: {stop_loss:.4f}, TP: {take_profit:.4f}")

    # Check existing positions for stop-loss/take-profit
    closed_positions = []
    for position in positions:
        entry_price, stop_loss, take_profit, direction = position
        if direction == "buy":
            if df['low'][i] <= stop_loss:  # Stop-loss hit
                profit = (stop_loss - entry_price) * 100000 * lot_size
                balance += profit
                print(f"Stop-Loss Hit (Buy) at {df.index[i]} - Price: {stop_loss:.4f}, Profit: {profit:.2f}")
                closed_positions.append(position)
            elif df['high'][i] >= take_profit:  # Take-profit hit
                profit = (take_profit - entry_price) * 100000 * lot_size
                balance += profit
                print(f"Take-Profit Hit (Buy) at {df.index[i]} - Price: {take_profit:.4f}, Profit: {profit:.2f}")
                closed_positions.append(position)
        elif direction == "sell":
            if df['high'][i] >= stop_loss:  # Stop-loss hit
                profit = (entry_price - stop_loss) * 100000 * lot_size
                balance += profit
                print(f"Stop-Loss Hit (Sell) at {df.index[i]} - Price: {stop_loss:.4f}, Profit: {profit:.2f}")
                closed_positions.append(position)
            elif df['low'][i] <= take_profit:  # Take-profit hit
                profit = (entry_price - take_profit) * 100000 * lot_size
                balance += profit
                print(f"Take-Profit Hit (Sell) at {df.index[i]} - Price: {take_profit:.4f}, Profit: {profit:.2f}")
                closed_positions.append(position)

    # Remove closed positions
    for position in closed_positions:
        positions.remove(position)

    # Track equity over time
    equity_curve.append(balance)

# Plot the equity curve
plt.figure(figsize=(12, 6))
plt.plot(df.index[-len(equity_curve):], equity_curve, label="Equity Curve")
plt.title("Conservative Intraday Backtest Results")
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
