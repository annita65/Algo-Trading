import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timedelta
from ta.trend import EMAIndicator
from ta.momentum import RSIIndicator
from ta.volatility import AverageTrueRange
import time

# Initialize MetaTrader 5 connection
if not mt5.initialize():
    print("Failed to initialize MT5!")
    quit()

# Define symbol and timeframe
symbol = "GBPUSD"  # Symbol for live trading
timeframe = mt5.TIMEFRAME_M1  # 1-minute candles
lot_size = 0.1  # Fixed lot size
atr_multiplier_sl = 1.5  # Stop-loss = 1.5 ATR
atr_multiplier_tp = 2  # Take-profit = 2 ATR
cooldown_period = timedelta(minutes=1)  # Minimum time between trades
last_trade_time = None  # Tracks the time of the last trade

# Fetch historical data
def fetch_data(symbol, timeframe, lookback=200):
    """
    Fetch historical data for the given symbol and timeframe.
    """
    now = datetime.now()
    rates = mt5.copy_rates_from(symbol, timeframe, now, lookback)
    if rates is None or len(rates) == 0:
        print(f"Failed to fetch data for {symbol}.")
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
    df['EMA_9'] = EMAIndicator(close=df['close'], window=9).ema_indicator()
    df['EMA_21'] = EMAIndicator(close=df['close'], window=21).ema_indicator()
    df['RSI'] = RSIIndicator(close=df['close'], window=14).rsi()
    atr = AverageTrueRange(high=df['high'], low=df['low'], close=df['close'], window=14)
    df['ATR'] = atr.average_true_range()
    return df

# Place order
def place_order(symbol, action, lot, sl_price, tp_price):
    """
    Place a market order with the given parameters.
    """
    # Corrected order type
    order_type = mt5.ORDER_TYPE_BUY if action == "buy" else mt5.ORDER_TYPE_SELL
    
    # Get the price based on action (buy or sell)
    price = mt5.symbol_info_tick(symbol).ask if action == "buy" else mt5.symbol_info_tick(symbol).bid

    # Create the order request
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": lot,
        "type": order_type,
        "price": price,
        "sl": sl_price,
        "tp": tp_price,
        "deviation": 10,
        "magic": 123456,  # Unique ID for this strategy
        "comment": "Live Trading Strategy",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    # Send the order
    result = mt5.order_send(request)
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        print(f"Order failed: {result.retcode}")
        return False
    print(f"Order placed: {action}, Volume: {lot}, SL: {sl_price}, TP: {tp_price}")
    return True

# Main loop for live trading
try:
    while True:
        now = datetime.now()

        # Fetch and prepare data
        df = fetch_data(symbol, timeframe)
        if df is None or len(df) < 21:
            print(f"Not enough data for {symbol}.")
            time.sleep(60)  # Wait before retrying
            continue

        df = calculate_indicators(df)
        latest = df.iloc[-1]
        atr = latest['ATR']

        # Avoid overtrading (cooldown)
        if last_trade_time and (now - last_trade_time) < cooldown_period:
            time.sleep(10)  # Short wait before the next check
            continue

        # Buy signal
        if (
            latest['EMA_9'] > latest['EMA_21']
            and latest['RSI'] > 50
        ):
            sl_price = latest['close'] - (atr * atr_multiplier_sl)
            tp_price = latest['close'] + (atr * atr_multiplier_tp)
            if place_order(symbol, "buy", lot_size, sl_price, tp_price):
                last_trade_time = now

        # Sell signal
        elif (
            latest['EMA_9'] < latest['EMA_21']
            and latest['RSI'] < 50
        ):
            sl_price = latest['close'] + (atr * atr_multiplier_sl)
            tp_price = latest['close'] - (atr * atr_multiplier_tp)
            if place_order(symbol, "sell", lot_size, sl_price, tp_price):
                last_trade_time = now

        time.sleep(10)  # Check every 10 seconds

except KeyboardInterrupt:
    print("Terminating the script...")

finally:
    # Shutdown MetaTrader 5 connection
    mt5.shutdown()
