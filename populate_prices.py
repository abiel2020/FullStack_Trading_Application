from warnings import catch_warnings
import config, sqlite3
import alpaca_trade_api as tradeapi
from alpaca_trade_api import TimeFrame, TimeFrameUnit
from datetime import date
connection = sqlite3.connect(config.DB_FILE)
connection.row_factory = sqlite3.Row
cursor = connection.cursor()

cursor.execute("""SELECT id, symbol, name FROM stock""")

rows = cursor.fetchall()

symbols = []
stock_dict = {}

for row in rows:
    symbol = row['symbol']
    symbols.append(symbol)
    stock_dict[symbol] = row['id']

api = tradeapi.REST(config.API_KEY, config.SECRET_KEY, base_url=config.API_URL)

chunk_size = 500

for i in range(0, len(symbols), chunk_size):
    symbol_chunk = symbols[i:i+chunk_size]
    try:
        bars = api.get_bars(symbol_chunk, TimeFrame(1,TimeFrameUnit.Day), "2023-12-12", adjustment='raw')
    except Exception as e:
        #print(f"Error fetching bars: {e}")
        continue  # Skip to the next chunk if there's an error

    for bar in bars:
        print(f"processing symbol {bar.S}")
        stock_id = stock_dict[bar.S]
        cursor.execute("""
            INSERT INTO stock_price(stock_id, date, open, high, low, close, volume)
            VALUES(?,?,?,?,?,?,?)""", (stock_id, bar.t.date(), bar.o, bar.h, bar.l, bar.c, bar.v))
        #print((stock_id, bar.t.date(), bar.o, bar.h, bar.l, bar.c, bar.v))

connection.commit()