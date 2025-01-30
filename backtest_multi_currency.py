import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timedelta
from ta.trend import EMAIndicator
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands, AverageTrueRange
import matplotlib.pyplot as plt

# Initialize MetaTrader 5 connection
if not mt5.initialize():
    print("Failed to initialize MT5!")
    quit()

# Define symbols and timeframe
symbols = ["EURUSD", "GBPUSD", "USDJPY"]  # List of symbols to backtest
timeframe = mt5.TIMEFRAME_H4  # 1-minute candles for scalping
start_date = datetime(2024, 1, 1, 0, 0)  # Start of the backtest period
end_date = datetime(2024, 12, 31, 23, 59)  # End of the backtest period

# Trading parameters
lot_size = 0.1  # Lot size per trade
atr_multiplier_sl = 1  # Stop-loss = 1 ATR
atr_multiplier_tp = 1.5  # Take-profit = 1.5 ATR

# Fetch historical data
def fetch_historical_data(symbol, timeframe, start_date, end_date):
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
    df['EMA_9'] = EMAIndicator(close=df['close'], window=9).ema_indicator()
    df['EMA_21'] = EMAIndicator(close=df['close'], window=21).ema_indicator()
    df['RSI'] = RSIIndicator(close=df['close'], window=14).rsi()
    bb = BollingerBands(close=df['close'], window=20, window_dev=2)
    df['bb_high'] = bb.bollinger_hband()
    df['bb_low'] = bb.bollinger_lband()
    atr = AverageTrueRange(high=df['high'], low=df['low'], close=df['close'], window=14)
    df['ATR'] = atr.average_true_range()
    return df

# Backtest function
def backtest_strategy(df):
    initial_balance = 10000  # Starting capital in USD
    balance = initial_balance
    positions = []
    equity_curve = []  # To store the balance over time

    for i in range(21, len(df)):  # Start after sufficient data for indicators
        row = df.iloc[i]
        atr = row['ATR']
        if pd.isna(atr):  # Skip if ATR is not available
            continue

        # Close open positions
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
        if row['EMA_9'] > row['EMA_21'] and row['RSI'] > 30 and row['close'] <= row['bb_low']:
            # Buy signal
            entry_price = row['close']
            sl = entry_price - (atr * atr_multiplier_sl)
            tp = entry_price + (atr * atr_multiplier_tp)
            positions.append((entry_price, sl, tp, "buy"))
        elif row['EMA_9'] < row['EMA_21'] and row['RSI'] < 70 and row['close'] >= row['bb_high']:
            # Sell signal
            entry_price = row['close']
            sl = entry_price + (atr * atr_multiplier_sl)
            tp = entry_price - (atr * atr_multiplier_tp)
            positions.append((entry_price, sl, tp, "sell"))

        # Track equity
        equity_curve.append(balance)

    return initial_balance, balance, equity_curve

# Main execution
results = []  # To store results for each symbol
for symbol in symbols:
    print(f"Backtesting {symbol}...")
    df = fetch_historical_data(symbol, timeframe, start_date, end_date)
    if df is None:
        continue
    df = calculate_indicators(df)
    initial_balance, final_balance, equity_curve = backtest_strategy(df)

    # Store results
    results.append({
        "Symbol": symbol,
        "Initial Balance": initial_balance,
        "Final Balance": final_balance,
        "Net Profit": final_balance - initial_balance
    })

    # Plot equity curve for each symbol
    plt.figure(figsize=(12, 6))
    plt.plot(df.index[-len(equity_curve):], equity_curve, label=f"Equity Curve ({symbol})")
    plt.title(f"Equity Curve for {symbol}")
    plt.xlabel("Date")
    plt.ylabel("Balance (USD)")
    plt.legend()
    plt.grid()
    plt.show()

# Print summary results
print("\nSummary Results:")
for result in results:
    print(f"Symbol: {result['Symbol']}, Initial Balance: ${result['Initial Balance']:.2f}, "
          f"Final Balance: ${result['Final Balance']:.2f}, "
          f"Net Profit: ${result['Net Profit']:.2f}")

# Shutdown MetaTrader 5 connection
mt5.shutdown()
