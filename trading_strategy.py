import MetaTrader5 as mt5
import pandas as pd

# Initialize MetaTrader 5 connection
if not mt5.initialize():
    print("Failed to initialize MT5!")
    quit()

# Define the symbol to trade
symbol = "EURUSD"
if not mt5.symbol_select(symbol, True):
    print(f"Failed to select symbol {symbol}")
    mt5.shutdown()
    quit()

# Fetch live data (last 100 candlesticks, 1-minute timeframe)
rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, 100)
df = pd.DataFrame(rates)
df['time'] = pd.to_datetime(df['time'], unit='s')  # Convert timestamps

# Calculate 10-period and 30-period Simple Moving Averages
df['SMA_10'] = df['close'].rolling(window=10).mean()
df['SMA_30'] = df['close'].rolling(window=30).mean()

# Define the trading strategy
def trading_strategy(df):
    # Check if SMA_10 crosses above SMA_30 (Buy Signal)
    if df['SMA_10'].iloc[-1] > df['SMA_30'].iloc[-1] and \
       df['SMA_10'].iloc[-2] <= df['SMA_30'].iloc[-2]:
        return "buy"

    # Check if SMA_10 crosses below SMA_30 (Sell Signal)
    elif df['SMA_10'].iloc[-1] < df['SMA_30'].iloc[-1] and \
         df['SMA_10'].iloc[-2] >= df['SMA_30'].iloc[-2]:
        return "sell"

    return None

# Place a trade order
def place_order(signal):
    if signal == "buy":
        order = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": 0.1,  # Lot size
            "type": mt5.ORDER_TYPE_BUY,
            "price": mt5.symbol_info_tick(symbol).ask,
            "sl": 0.0,  # Stop loss
            "tp": 0.0,  # Take profit
            "deviation": 10,  # Allowed price deviation
        }
        result = mt5.order_send(order)
        if result.retcode == mt5.TRADE_RETCODE_DONE:
            print("Buy order placed successfully!")
        else:
            print(f"Failed to place buy order: {result.retcode}")
    elif signal == "sell":
        order = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": 0.1,  # Lot size
            "type": mt5.ORDER_TYPE_SELL,
            "price": mt5.symbol_info_tick(symbol).bid,
            "sl": 0.0,  # Stop loss
            "tp": 0.0,  # Take profit
            "deviation": 10,  # Allowed price deviation
        }
        result = mt5.order_send(order)
        if result.retcode == mt5.TRADE_RETCODE_DONE:
            print("Sell order placed successfully!")
        else:
            print(f"Failed to place sell order: {result.retcode}")
    else:
        print("No valid signal to place an order.")

# Run the trading strategy
signal = trading_strategy(df)
print(f"Trading Signal: {signal}")
place_order(signal)

# Shutdown MetaTrader connection
mt5.shutdown()
