import MetaTrader5 as mt5
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from ta.trend import EMAIndicator
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands, AverageTrueRange

# Initialize MetaTrader 5 connection
if not mt5.initialize():
    print("Failed to initialize MT5!")
    quit()

# Define symbol and timeframe
symbol = "BTCUSD"  # Focus on a volatile instrument 
timeframe = mt5.TIMEFRAME_M1  # Scalping on 1-minute candles

# Define the testing period
start_date = datetime(2024, 3 , 1, 0, 0)  # Start date
end_date = datetime(2024, 3, 31, 23, 59)  # End date (adjust as needed)

# Trading parameters
initial_balance = 10000  # Starting capital
lot_size = 0.1  # Fixed lot size
atr_multiplier_sl = 1  # Stop-loss = 1 ATR
atr_multiplier_tp = 1.5  # Take-profit = 1.5 ATR
cooldown_period = timedelta(minutes=2)  # Minimum time between trades
last_trade_time = None  # Track last trade time

# Fetch historical data
rates = mt5.copy_rates_range(symbol, timeframe, start_date, end_date)
if rates is None or len(rates) == 0:
    print(f"No data available for {symbol}. Exiting...")
    mt5.shutdown()
    quit()

# Convert to DataFrame
df = pd.DataFrame(rates)
df['time'] = pd.to_datetime(df['time'], unit='s')
df.set_index('time', inplace=True)

# Debugging: Print the number of rows and first few rows of data
print(f"Number of rows fetched: {len(df)}")
print(df.head())

# Ensure there are enough rows for ATR calculation
if len(df) < 14:  # ATR requires at least 14 rows
    print(f"Insufficient rows for ATR calculation. Rows available: {len(df)}")
    mt5.shutdown()
    quit()

# Calculate indicators
df['EMA_9'] = EMAIndicator(close=df['close'], window=9).ema_indicator()
df['EMA_21'] = EMAIndicator(close=df['close'], window=21).ema_indicator()
df['RSI'] = RSIIndicator(close=df['close'], window=14).rsi()
bb = BollingerBands(close=df['close'], window=20, window_dev=2)
df['bb_high'] = bb.bollinger_hband()
df['bb_low'] = bb.bollinger_lband()
atr = AverageTrueRange(high=df['high'], low=df['low'], close=df['close'], window=14)
df['ATR'] = atr.average_true_range()

# Debugging: Print the calculated indicators
print("Indicators calculated successfully.")
print(df[['EMA_9', 'EMA_21', 'RSI', 'bb_high', 'bb_low', 'ATR']].head())

# Backtesting logic
balance = initial_balance
positions = []  # Track open positions
equity_curve = []  # Track balance over time

for i in range(21, len(df)):  # Start after enough data for EMA and ATR
    atr_value = df['ATR'][i]
    if pd.isna(atr_value):  # Skip if ATR is not available
        continue

    current_price = df['close'][i]
    ema_9 = df['EMA_9'][i]
    ema_21 = df['EMA_21'][i]
    rsi = df['RSI'][i]

    # Ensure cooldown period is respected
    if last_trade_time is not None and (df.index[i] - last_trade_time) < cooldown_period:
        equity_curve.append(balance)
        continue

    # Buy signal: EMA 9 > EMA 21, RSI > 30, and price near lower Bollinger Band
    if ema_9 > ema_21 and rsi > 30 and current_price <= df['bb_low'][i]:
        entry_price = current_price
        stop_loss = entry_price - (atr_value * atr_multiplier_sl)
        take_profit = entry_price + (atr_value * atr_multiplier_tp)
        positions.append((entry_price, stop_loss, take_profit, "buy"))
        last_trade_time = df.index[i]
        print(f"Buy signal on {df.index[i]} at {entry_price:.4f}")

    # Sell signal: EMA 9 < EMA 21, RSI < 70, and price near upper Bollinger Band
    elif ema_9 < ema_21 and rsi < 70 and current_price >= df['bb_high'][i]:
        entry_price = current_price
        stop_loss = entry_price + (atr_value * atr_multiplier_sl)
        take_profit = entry_price - (atr_value * atr_multiplier_tp)
        positions.append((entry_price, stop_loss, take_profit, "sell"))
        last_trade_time = df.index[i]
        print(f"Sell signal on {df.index[i]} at {entry_price:.4f}")

    # Check open positions
    closed_positions = []
    for position in positions:
        entry_price, stop_loss, take_profit, direction = position
        if direction == "buy":
            if df['low'][i] <= stop_loss:  # Stop-loss hit
                balance -= (entry_price - stop_loss) * 100000 * lot_size
                print(f"Stop-loss hit (Buy) on {df.index[i]}: {stop_loss:.4f}")
                closed_positions.append(position)
            elif df['high'][i] >= take_profit:  # Take-profit hit
                balance += (take_profit - entry_price) * 100000 * lot_size
                print(f"Take-profit hit (Buy) on {df.index[i]}: {take_profit:.4f}")
                closed_positions.append(position)
        elif direction == "sell":
            if df['high'][i] >= stop_loss:  # Stop-loss hit
                balance -= (stop_loss - entry_price) * 100000 * lot_size
                print(f"Stop-loss hit (Sell) on {df.index[i]}: {stop_loss:.4f}")
                closed_positions.append(position)
            elif df['low'][i] <= take_profit:  # Take-profit hit
                balance += (entry_price - take_profit) * 100000 * lot_size
                print(f"Take-profit hit (Sell) on {df.index[i]}: {take_profit:.4f}")
                closed_positions.append(position)

    # Remove closed positions
    for position in closed_positions:
        positions.remove(position)

    # Track equity
    equity_curve.append(balance)

# Plot the equity curve
plt.figure(figsize=(12, 6))
plt.plot(df.index[-len(equity_curve):], equity_curve, label="Equity Curve")
plt.title(f"Scalping Strategy Backtest Results for {symbol}")
plt.xlabel("Time")
plt.ylabel("Balance (USD)")
plt.legend()
plt.grid()
plt.show()

# Print results
print(f"Initial Balance: ${initial_balance}")
print(f"Final Balance: ${balance:.2f}")
print(f"Net Profit: ${balance - initial_balance:.2f}")

# Shutdown MetaTrader 5 connection
mt5.shutdown()
