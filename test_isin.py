import yfinance as yf


def get_isin(ticker):
    try:
        t = yf.Ticker(ticker)
        return t.isin
    except Exception as e:
        return str(e)


tickers = ["AMD", "ASML", "MSFT"]
for ticker in tickers:
    print(f"{ticker}: {get_isin(ticker)}")
