import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timedelta
from ta.trend import EMAIndicator
from ta.momentum import RSIIndicator
from ta.volatility import AverageTrueRange
import matplotlib.pyplot as plt

# Initialize MetaTrader 5 connection
if not mt5.initialize():
    print("Failed to initialize MT5!")
    quit()

# Define symbol and timeframe
symbol = "EURUSD"  # Replace with your preferred symbol
timeframe = mt5.TIMEFRAME_M15  # 5-minute candles for intraday trading
start_date = datetime(2023, 1, 1)  # Start of the backtest period
end_date = datetime(2023, 1, 31)  # End of the backtest period

# Trading parameters
lot_size = 0.1  # Lot size per trade
atr_multiplier_sl = 1.5  # Stop-loss = 2 ATR
atr_multiplier_tp = 2  # Take-profit = 4 ATR
session_close_time = 16  # Close positions at 4 PM (local time)

# Fetch historical data
def fetch_historical_data(symbol, timeframe, start_date, end_date):
    """
    Fetch historical data for the given symbol and timeframe.
    """
    rates = mt5.copy_rates_range(symbol, timeframe, start_date, end_date)
    if rates is None or len(rates) == 0:
        print(f"No data available for {symbol} in the given date range.")
        return None
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df.set_index('time', inplace=True)
    return df

# Calculate indicators
def calculate_indicators(df):
    """
    Calculate EMA, RSI, and ATR indicators.
    """
    df['EMA_20'] = EMAIndicator(close=df['close'], window=20).ema_indicator()
    df['EMA_50'] = EMAIndicator(close=df['close'], window=50).ema_indicator()
    df['RSI'] = RSIIndicator(close=df['close'], window=14).rsi()
    atr = AverageTrueRange(high=df['high'], low=df['low'], close=df['close'], window=14)
    df['ATR'] = atr.average_true_range()
    return df

# Backtest function
def backtest_strategy(df):
    """
    Backtest the intraday strategy using historical data.
    """
    initial_balance = 10000  # Starting capital in USD
    balance = initial_balance
    positions = []
    equity_curve = []  # To store the balance over time

    for i in range(50, len(df)):  # Start after sufficient data for indicators
        row = df.iloc[i]
        atr = row['ATR']
        if pd.isna(atr):  # Skip if ATR is not available
            continue

        # Close open positions by session end
        current_time = row.name
        if current_time.hour >= session_close_time and positions:
            for position in positions:
                entry_price, sl, tp, direction = position
                if direction == "buy":
                    balance += (row['close'] - entry_price) * 100000 * lot_size
                elif direction == "sell":
                    balance += (entry_price - row['close']) * 100000 * lot_size
            positions = []  # Clear all positions
            continue

        # Close open positions with SL/TP
        closed_positions = []
        for position in positions:
            entry_price, sl, tp, direction = position
            if direction == "buy":
                if row['low'] <= sl:  # Stop-loss hit
                    balance -= (entry_price - sl) * 100000 * lot_size
                    closed_positions.append(position)
                elif row['high'] >= tp:  # Take-profit hit
                    balance += (tp - entry_price) * 100000 * lot_size
                    closed_positions.append(position)
            elif direction == "sell":
                if row['high'] >= sl:  # Stop-loss hit
                    balance -= (sl - entry_price) * 100000 * lot_size
                    closed_positions.append(position)
                elif row['low'] <= tp:  # Take-profit hit
                    balance += (entry_price - tp) * 100000 * lot_size
                    closed_positions.append(position)

        for position in closed_positions:
            positions.remove(position)

        # Entry signals
        if row['EMA_20'] > row['EMA_50'] and row['RSI'] > 50:
            # Buy signal
            entry_price = row['close']
            sl = entry_price - (atr * atr_multiplier_sl)
            tp = entry_price + (atr * atr_multiplier_tp)
            positions.append((entry_price, sl, tp, "buy"))
        elif row['EMA_20'] < row['EMA_50'] and row['RSI'] < 50:
            # Sell signal
            entry_price = row['close']
            sl = entry_price + (atr * atr_multiplier_sl)
            tp = entry_price - (atr * atr_multiplier_tp)
            positions.append((entry_price, sl, tp, "sell"))

        # Track equity
        equity_curve.append(balance)

    return initial_balance, balance, equity_curve

# Main execution
df = fetch_historical_data(symbol, timeframe, start_date, end_date)
if df is not None:
    df = calculate_indicators(df)
    initial_balance, final_balance, equity_curve = backtest_strategy(df)

    # Print results
    print(f"Initial Balance: ${initial_balance}")
    print(f"Final Balance: ${final_balance:.2f}")
    print(f"Net Profit: ${final_balance - initial_balance:.2f}")

    # Plot equity curve
    plt.figure(figsize=(12, 6))
    plt.plot(df.index[-len(equity_curve):], equity_curve, label="Equity Curve")
    plt.title(f"Intraday Strategy Equity Curve ({symbol})")
    plt.xlabel("Date")
    plt.ylabel("Balance (USD)")
    plt.legend()
    plt.grid()
    plt.show()

# Shutdown MetaTrader 5 connection
mt5.shutdown()
