from warnings import catch_warnings
import config, sqlite3
import alpaca_trade_api as tradeapi
from alpaca_trade_api import TimeFrame, TimeFrameUnit
from datetime import date
import tulipy, numpy

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
current_date = date.today().isoformat()
for i in range(0, len(symbols), chunk_size):
    symbol_chunk = symbols[i:i+chunk_size]
    try:
        bars = api.get_bars(symbol_chunk, TimeFrame(1,TimeFrameUnit.Day), start="2023-10-10", adjustment='raw')
    except Exception as e:
        #print(f"Error fetching bars: {e}")
        continue  # Skip to the next chunk if there's an error

    # Extract relevant data
    symbol_data = {}
    for bar in bars:
        symbol_data.setdefault(bar.S, []).append(bar)

    # Batch insert data into the database
    batch_data = []
    for symbol, bars in symbol_data.items():
        print(f"Inserting data for {symbol}...")
        recent_closes = [bar.c for bar in bars]
        if len(recent_closes) >= 50 and "2023-12-22" == bars[-1].t.date().isoformat():
            sma_20 = tulipy.sma(numpy.array(recent_closes), period=20)[-1]
            sma_50 = tulipy.sma(numpy.array(recent_closes), period=50)[-1]
            rsi_14 = tulipy.rsi(numpy.array(recent_closes), period=14)[-1]
        else:
            sma_20, sma_50, rsi_14 = None, None, None

        stock_id = stock_dict[symbol]
        batch_data.append((stock_id, bars[-1].t.date(), bars[-1].o, bars[-1].h, bars[-1].l, bars[-1].c, bars[-1].v, sma_20, sma_50, rsi_14))

    # Use executemany for batch insert
    cursor.executemany("""
        INSERT INTO stock_price(stock_id, date, open, high, low, close, volume, sma_20, sma_50, rsi_14)
        VALUES(?,?,?,?,?,?,?,?,?,?)""", batch_data)


connection.commit()