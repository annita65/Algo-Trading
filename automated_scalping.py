import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timedelta
from ta.trend import EMAIndicator
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands, AverageTrueRange
import time

# Initialize MetaTrader 5 connection
if not mt5.initialize():
    print("Failed to initialize MT5!")
    quit()

# Define symbols and timeframe
symbols = ["EURUSD", "GBPUSD"]
timeframe = mt5.TIMEFRAME_M1  # Scalping on 1-minute candles

# Trading parameters
lot_size = 0.1  # Fixed lot size
atr_multiplier_sl = 1  # Stop-loss = 1 ATR
atr_multiplier_tp = 1.5  # Take-profit = 1.5 ATR
cooldown_period = timedelta(minutes=2)  # Minimum time between trades per symbol

# Store last trade times for cooldown
last_trade_time = {symbol: None for symbol in symbols}

# Define the scalping strategy
def fetch_data(symbol, timeframe, lookback=200):
    """
    Fetch historical data for the given symbol and timeframe.
    """
    now = datetime.now()
    rates = mt5.copy_rates_from(symbol, timeframe, now, lookback)
    if rates is None or len(rates) == 0:
        return None
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df.set_index('time', inplace=True)
    return df

def calculate_indicators(df):
    """
    Calculate EMA, RSI, Bollinger Bands, and ATR indicators.
    """
    df['EMA_9'] = EMAIndicator(close=df['close'], window=9).ema_indicator()
    df['EMA_21'] = EMAIndicator(close=df['close'], window=21).ema_indicator()
    df['RSI'] = RSIIndicator(close=df['close'], window=14).rsi()
    bb = BollingerBands(close=df['close'], window=20, window_dev=2)
    df['bb_high'] = bb.bollinger_hband()
    df['bb_low'] = bb.bollinger_lband()
    atr = AverageTrueRange(high=df['high'], low=df['low'], close=df['close'], window=14)
    df['ATR'] = atr.average_true_range()
    return df

def place_order(symbol, action, lot, sl_price, tp_price):
    """
    Place a market order with the given parameters.
    """
    order_type = mt5.ORDER_BUY if action == "buy" else mt5.ORDER_SELL
    price = mt5.symbol_info_tick(symbol).ask if action == "buy" else mt5.symbol_info_tick(symbol).bid
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
        "comment": "Automated Scalping",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    result = mt5.order_send(request)
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        print(f"Order failed for {symbol}. Error code: {result.retcode}")
        return False
    print(f"Order placed: {symbol}, {action}, Volume: {lot}, SL: {sl_price}, TP: {tp_price}")
    return True

# Main loop
try:
    while True:
        now = datetime.now()
        # Check if the market is open (Monday-Friday)
        if now.weekday() >= 5:  # Skip weekends
            print("Market closed. Waiting for Monday...")
            time.sleep(3600)  # Sleep for 1 hour
            continue

        for symbol in symbols:
            print(f"Checking {symbol}...")
            
            # Fetch and prepare data
            df = fetch_data(symbol, timeframe)
            if df is None:
                print(f"Failed to fetch data for {symbol}.")
                continue

            df = calculate_indicators(df)
            if len(df) < 21:  # Ensure sufficient data for indicators
                print(f"Not enough data for indicators on {symbol}.")
                continue

            # Get the latest row
            latest = df.iloc[-1]
            atr = latest['ATR']
            if pd.isna(atr):  # Skip if ATR is unavailable
                continue

            # Avoid overtrading (cooldown)
            if last_trade_time[symbol] is not None and (now - last_trade_time[symbol]) < cooldown_period:
                continue

            # Buy signal: EMA 9 > EMA 21, RSI > 30, and price near lower Bollinger Band
            if (
                latest['EMA_9'] > latest['EMA_21']
                and latest['RSI'] > 30
                and latest['close'] <= latest['bb_low']
            ):
                sl_price = latest['close'] - (atr * atr_multiplier_sl)
                tp_price = latest['close'] + (atr * atr_multiplier_tp)
                if place_order(symbol, "buy", lot_size, sl_price, tp_price):
                    last_trade_time[symbol] = now

            # Sell signal: EMA 9 < EMA 21, RSI < 70, and price near upper Bollinger Band
            elif (
                latest['EMA_9'] < latest['EMA_21']
                and latest['RSI'] < 70
                and latest['close'] >= latest['bb_high']
            ):
                sl_price = latest['close'] + (atr * atr_multiplier_sl)
                tp_price = latest['close'] - (atr * atr_multiplier_tp)
                if place_order(symbol, "sell", lot_size, sl_price, tp_price):
                    last_trade_time[symbol] = now

        # Wait before the next iteration
        time.sleep(60)  # Check every 1 minute

except KeyboardInterrupt:
    print("Terminating the script...")

finally:
    # Shutdown MT5 connection
    mt5.shutdown()
