import yfinance

df = yfinance.download('APPL', start='202-01-01', end='2020-10-02')
df.to_csv('APPL.csv')
