import config, sqlite3
import alpaca_trade_api as tradeapi
from datetime import date
from alpaca_trade_api import TimeFrame, TimeFrameUnit
from timezone import is_dst
import tulipy

connection = sqlite3.connect(config.DB_FILE)
connection.row_factory = sqlite3.Row

cursor = connection.cursor()

cursor.execute("""
    SELECT id FROM strategy WHERE name = 'bollinger_bands'
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

current_date = date.today().isoformat()

start_min_bar = f"{current_date} 09:30:00-05:00"
end_min_bar = f"{current_date} 10:30:00-05:00"

api = tradeapi.REST(config.API_KEY, config.SECRET_KEY, base_url=config.API_URL)

orders = api.list_orders(status='all', after={current_date})
existing_order_symbols = [order.symbol for order in orders if order.status != 'cancelled']

messages = []

for symbol in symbols:
    minute_bars = api.get_bars(symbol,TimeFrame(1,TimeFrameUnit.Minute), start="2023-10-10").df
    market_open_mask = (minute_bars.index >= start_min_bar) & (minute_bars.index < end_min_bar)
    market_open_bars = minute_bars.loc[ market_open_mask]
    
    if(len(market_open_bars) >= 20):
        closes = market_open_bars.close.values

        lower, middle, upper = tulipy.bbands(closes, period=20, stddev=2)

        current_candle = market_open_bars.iloc[-1]
        previous_candle = market_open_bars.iloc[-2]

        if current_candle.close > lower[-1] and previous_candle.close  < lower[-2]:
            print(f"{symbol}closed above lower band")
            print(current_candle)
            if symbol not in existing_order_symbols:
                    limit_price = current_candle.close

                    api.submit_order(
                        symbol= symbol,
                        side='buy',
                        type='limit',
                        qty='100',
                        time_in_force='day',
                        order_class='bracket',
                        limit_price=round(limit_price, 1),
                        take_profit=dict(
                            limit_price= limit_price - (candle_range * 3 ),
                        ),
                        stop_loss=dict(
                            stop_price= previous_candle.low,
                        )
                    )
            else:
                print(f"Already in order for {symbol}, skipping")