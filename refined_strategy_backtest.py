import MetaTrader5 as mt5
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from ta.volatility import AverageTrueRange, BollingerBands
from ta.momentum import RSIIndicator

# Initialize MetaTrader 5 connection
if not mt5.initialize():
    print("Failed to initialize MT5!")
    quit()

# Define symbol and timeframe
symbol = "EURUSD"
timeframe = mt5.TIMEFRAME_M1  # 1-minute timeframe

# Define the day for intraday trading (today by default)
today = datetime.now().date()
start_time = datetime(today.year, today.month, today.day - 5, 6, 0)  # Start fetching data 5 days earlier at 6:00 AM UTC
end_time = datetime(today.year, today.month, today.day, 17, 0)  # End trading at 5:00 PM UTC

# Fetch historical data for the day
rates = mt5.copy_rates_range(symbol, timeframe, start_time, end_time)
if rates is None or len(rates) < 30:  # Ensure at least 30 rows for calculations
    print(f"Insufficient historical data for backtesting. Rows fetched: {len(rates) if rates else 0}")
    mt5.shutdown()
    quit()

# Convert to a pandas DataFrame
df = pd.DataFrame(rates)
df['time'] = pd.to_datetime(df['time'], unit='s')  # Convert timestamp
df.set_index('time', inplace=True)

# Ensure there are enough rows for ATR calculation
if len(df) >= 14:  # ATR requires at least 14 rows
    df['ATR'] = AverageTrueRange(high=df['high'], low=df['low'], close=df['close'], window=14).average_true_range()
else:
    print("Not enough data to calculate ATR")
    mt5.shutdown()
    quit()

# Calculate Moving Averages, RSI, and Bollinger Bands
df['SMA_10'] = df['close'].rolling(window=10).mean()
df['SMA_30'] = df['close'].rolling(window=30).mean()
df['RSI'] = RSIIndicator(close=df['close'], window=14).rsi()
bb = BollingerBands(close=df['close'], window=20, window_dev=2)
df['bb_high'] = bb.bollinger_hband()
df['bb_low'] = bb.bollinger_lband()

# Define trading parameters
initial_balance = 10000  # Initial capital in USD
balance = initial_balance
lot_size = 0.1  # Lot size per trade (fixed)
positions = []  # Track open positions
equity_curve = []  # Track balance over time
cooldown_period = timedelta(minutes=15)  # Cooldown between trades
last_trade_time = None  # Track the time of the last trade

# Backtest intraday strategy
for i in range(30, len(df)):
    # Ensure cooldown period is respected
    if last_trade_time is not None and (df.index[i] - last_trade_time) < cooldown_period:
        equity_curve.append(balance)
        continue

    # Check for buy signal
    if df['SMA_10'][i] > df['SMA_30'][i] and df['SMA_10'][i - 1] <= df['SMA_30'][i - 1] and df['RSI'][i] > 50 and df['close'][i] > df['bb_high'][i]:
        entry_price = df['close'][i]
        stop_loss = entry_price - (df['ATR'][i] * 1)  # 1 ATR below entry price
        take_profit = entry_price + (df['ATR'][i] * 2)  # 2 ATR above entry price
        positions.append((entry_price, stop_loss, take_profit, "buy"))
        last_trade_time = df.index[i]
        print(f"Buy Signal at {df.index[i]} - Price: {entry_price}, SL: {stop_loss}, TP: {take_profit}")

    # Check for sell signal
    elif df['SMA_10'][i] < df['SMA_30'][i] and df['SMA_10'][i - 1] >= df['SMA_30'][i - 1] and df['RSI'][i] < 50 and df['close'][i] < df['bb_low'][i]:
        entry_price = df['close'][i]
        stop_loss = entry_price + (df['ATR'][i] * 1)  # 1 ATR above entry price
        take_profit = entry_price - (df['ATR'][i] * 2)  # 2 ATR below entry price
        positions.append((entry_price, stop_loss, take_profit, "sell"))
        last_trade_time = df.index[i]
        print(f"Sell Signal at {df.index[i]} - Price: {entry_price}, SL: {stop_loss}, TP: {take_profit}")

    # Check existing positions for stop-loss/take-profit
    closed_positions = []
    for position in positions:
        entry_price, stop_loss, take_profit, direction = position
        if direction == "buy":
            if df['low'][i] <= stop_loss:  # Stop-loss hit
                profit = (stop_loss - entry_price) * 100000 * lot_size
                balance += profit
                print(f"Stop-Loss Hit (Buy) at {df.index[i]} - Price: {stop_loss}, Profit: {profit:.2f}")
                closed_positions.append(position)
            elif df['high'][i] >= take_profit:  # Take-profit hit
                profit = (take_profit - entry_price) * 100000 * lot_size
                balance += profit
                print(f"Take-Profit Hit (Buy) at {df.index[i]} - Price: {take_profit}, Profit: {profit:.2f}")
                closed_positions.append(position)
        elif direction == "sell":
            if df['high'][i] >= stop_loss:  # Stop-loss hit
                profit = (entry_price - stop_loss) * 100000 * lot_size
                balance += profit
                print(f"Stop-Loss Hit (Sell) at {df.index[i]} - Price: {stop_loss}, Profit: {profit:.2f}")
                closed_positions.append(position)
            elif df['low'][i] <= take_profit:  # Take-profit hit
                profit = (entry_price - take_profit) * 100000 * lot_size
                balance += profit
                print(f"Take-Profit Hit (Sell) at {df.index[i]} - Price: {take_profit}, Profit: {profit:.2f}")
                closed_positions.append(position)

    # Remove closed positions
    for position in closed_positions:
        positions.remove(position)

    # Track equity over time
    equity_curve.append(balance)

# Plot the equity curve
plt.figure(figsize=(12, 6))
plt.plot(df.index[-len(equity_curve):], equity_curve, label="Equity Curve")
plt.title("Refined Intraday Backtest Results")
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
