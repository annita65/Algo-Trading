import MetaTrader5 as mt5
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# Initialize MetaTrader 5 connection
if not mt5.initialize():
    print("Failed to initialize MT5!")
    quit()

# Define symbol and timeframe
symbol = "EURUSD"
timeframe = mt5.TIMEFRAME_M1  # 1-minute timeframe

# Define the day for intraday trading (today by default)
today = datetime.now().date()
start_time = datetime(today.year, today.month, today.day, 0, 0)  # Start of day
end_time = datetime(today.year, today.month, today.day, 23, 59)  # End of day

# Fetch historical data for the day
rates = mt5.copy_rates_range(symbol, timeframe, start_time, end_time)
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

# Define trading parameters
lot_size = 0.1  # Lot size per trade
initial_balance = 10000  # Initial capital in USD
balance = initial_balance
stop_loss_pips = 10  # Stop-loss in pips
take_profit_pips = 20  # Take-profit in pips
positions = []  # Track open positions
equity_curve = []  # Track balance over time

# Backtest intraday strategy
for i in range(30, len(df)):
    # Check for buy signal
    if df['SMA_10'][i] > df['SMA_30'][i] and df['SMA_10'][i - 1] <= df['SMA_30'][i - 1]:
        entry_price = df['close'][i]
        stop_loss = entry_price - stop_loss_pips * 0.0001  # Convert pips to price
        take_profit = entry_price + take_profit_pips * 0.0001
        positions.append((entry_price, stop_loss, take_profit, "buy"))
        print(f"Buy Signal at {df.index[i]} - Price: {entry_price}, SL: {stop_loss}, TP: {take_profit}")

    # Check for sell signal
    elif df['SMA_10'][i] < df['SMA_30'][i] and df['SMA_10'][i - 1] >= df['SMA_30'][i - 1]:
        entry_price = df['close'][i]
        stop_loss = entry_price + stop_loss_pips * 0.0001
        take_profit = entry_price - take_profit_pips * 0.0001
        positions.append((entry_price, stop_loss, take_profit, "sell"))
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
plt.title("Intraday Backtest Results")
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
