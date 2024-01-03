import config, sqlite3
import alpaca_trade_api as tradeapi
from datetime import date
from alpaca_trade_api import TimeFrame, TimeFrameUnit
import alpha_vantage 
from alpha_vantage.timeseries import TimeSeries
import smtplib, ssl
from timezone import is_dst
# Create a secure SSL context
context = ssl.create_default_context()

connection = sqlite3.connect(config.DB_FILE)
connection.row_factory = sqlite3.Row

cursor = connection.cursor()

cursor.execute("""
    SELECT id FROM strategy WHERE name = 'opening_range_breakdown'
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
if is_dst():
    start_min_bar = f"2023-12-18 09:30:00-05:00"
    end_min_bar = f"{current_date} 09:45:00-05:00"
else:
    start_min_bar = f"2023-12-18 09:30:00-04:00"
    end_min_bar = f"{current_date} 09:45:00-04:00"

api = tradeapi.REST(config.API_KEY, config.SECRET_KEY, base_url=config.API_URL)

orders = api.list_orders(status='all',limit=500, after=f"{current_date}T13:30:00Z")
existing_order_symbols = [order.symbol for order in orders if order.status != 'cancelled']

messages = []

for symbol in symbols:
    #minute_bars = get_minute_data(symbol)
    minute_bars = api.get_bars(symbol,TimeFrame(1,TimeFrameUnit.Minute), start="2023-12-18").df
    
    opening_range_mask = (minute_bars.index >= start_min_bar) & (minute_bars.index < end_min_bar)
    opening_range_bars = minute_bars.loc[opening_range_mask]
    
    opening_range_low = opening_range_bars['low'].min()
    opening_range_high = opening_range_bars['high'].max()
    opening_range = opening_range_high - opening_range_low

    after_opening_range_mask = minute_bars.index >= end_min_bar
    after_opening_range_bars = minute_bars.loc[after_opening_range_mask]

    after_opening_range_breakdown = after_opening_range_bars[after_opening_range_bars['close']<opening_range_high]

    if not after_opening_range_breakdown.empty:
        if symbol not in existing_order_symbols:
            limit_price = after_opening_range_breakdown.iloc[0]['close']

            message = f"selling short {symbol} at {limit_price}, closed below {opening_range_low}\n\n {after_opening_range_breakdown.iloc[0]}\n\n"

            messages.append(message)
            print(message)

            api.submit_order(
                symbol= symbol,
                side='sell',
                type='limit',
                qty='100',
                time_in_force='day',
                order_class='bracket',
                limit_price=round(limit_price, 1),
                take_profit=dict(
                    limit_price= round(limit_price - opening_range, 1),
                ),
                stop_loss=dict(
                    stop_price= round(limit_price + opening_range,1),
                )
            )
        else:
            print(f"Already in order for {symbol}, skipping")
print("sending email")

"""with smtplib.SMTP_SSL(config.EMAIL_HOST, config.EMAIL_PORT, context=context) as server:
    try:
        server.login(config.EMAIL_ADDRESS, config.EMAIL_PORT)
        # TODO: Send email here
    except Exception as e:
        print(f"Error fetching bars: {e}")
        
    email_message = f"Subject: Trade Notifications for {current_date}\n\n"
    email_message += "\n\n".join(messages)
    try:
        server.sendmail(config.EMAIL_ADDRESS, config.EMAIL_SMS, email_message)#sends sms
        server.sendmail(config.EMAIL_ADDRESS, config.EMAIL_ADDRESS, email_message)#sends email
    except Exception as e:
        print(f"Error fetching bars: {e}")
    print("sent email")
"""