import config, sqlite3
import alpaca_trade_api as tradeapi
from datetime import date
from alpaca_trade_api import TimeFrame, TimeFrameUnit
import alpha_vantage 
from alpha_vantage.timeseries import TimeSeries


def get_minute_data(ticker):
    ts = TimeSeries(key=config.ALPHA_KEY,
                    output_format='pandas', indexing_type='date')
    df, _ = ts.get_intraday(ticker, interval='1min', outputsize='full')

    df.rename(columns={"1. open": "open", "2. high": "high", "3. low": "low", "4. close": "close",
        "5. volume": "volume",  "date": "date"}, inplace=True)

    df = df.iloc[::-1]

    return df

connection = sqlite3.connect(config.DB_FILE)
connection.row_factory = sqlite3.Row

cursor = connection.cursor()

cursor.execute("""
    SELECT id FROM strategy WHERE name = 'opening_range_breakout'
    """)

strategy_id = cursor.fetchone()['id']

cursor.execute("""
    SELECT symbol, name
    FROM stock
    JOIN stock_strategy ON stock_strategy.stock_id = stock.id
    WHERE stock_strategy.strategy_id = ?
    """, (strategy_id,))

stocks = cursor.fetchall()
symbols = [stock['symbol'] for stock in stocks]


api = tradeapi.REST(config.API_KEY, config.SECRET_KEY, base_url=config.API_URL)

orders = api.list_orders()
existing_order_symbols = [order.symbol for order in orders]

current_date = date.today().isoformat()
start_min_bar = f"2023-12-18 09:30:00+00:00"
end_min_bar = f"{current_date} 09:45:00+00:00"

for symbol in symbols:
    #minute_bars = get_minute_data(symbol)
    minute_bars = api.get_bars(symbol,TimeFrame(1,TimeFrameUnit.Minute), start="2023-12-18").df
    
    print(symbol)
    
    opening_range_mask = (minute_bars.index >= start_min_bar) & (minute_bars.index < end_min_bar)
    opening_range_bars = minute_bars.loc[opening_range_mask]
    
    print(opening_range_bars)
    
    opening_range_low = opening_range_bars['low'].min()
    opening_range_high = opening_range_bars['high'].max()
    opening_range = opening_range_high - opening_range_low
    
    print(opening_range_low)
    print(opening_range_high)
    print(opening_range)

    after_opening_range_mask = minute_bars.index >= end_min_bar
    after_opening_range_bars = minute_bars.loc[after_opening_range_mask]
    
    print(after_opening_range_bars)

    after_opening_range_breakout = after_opening_range_bars[after_opening_range_bars['close']>opening_range_high]

    if not after_opening_range_breakout.empty:
        if symbol not in existing_order_symbols:
            print(after_opening_range_breakout)
            limit_price = after_opening_range_breakout.iloc[0]['close']
            print(limit_price)
            print(f"placing order for {symbol} at {limit_price}, closed above {opening_range_high} at {after_opening_range_breakout.iloc[0]}")

            api.submit_order(
                symbol= symbol,
                side='buy',
                type='limit',
                qty='100',
                time_in_force='day',
                order_class='bracket',
                limit_price=round(limit_price, 1),
                take_profit=dict(
                    limit_price= round(limit_price + opening_range, 1),
                ),
                stop_loss=dict(
                    stop_price= round(limit_price - opening_range,1),
                )
            )
        else:
            print(f"Already in order for {symbol}, skipping")