import json, os, yfinance as yf
from datetime import datetime, timezone
from pathlib import Path
STATE_PATH = Path('data/state.json')
CORE = ['PLTR','GOOG','NVDA','NOW','GEV','NBIS','TSM','AVGO','ALAB','LLY','MELI','SPOT','RKLB','SOFI','SPY','AMZN','MA','DASH','CRWD','ISRG']
def main():
    st = json.loads(STATE_PATH.read_text('utf-8')) if STATE_PATH.exists() else {}
    mkt = st.setdefault('mkt', {'quotes':{}, 'ma':{}, 'targets':{}})
    for t in CORE:
        try:
            h = yf.Ticker(t).history(period='1y', interval='1d', auto_adjust=False)
            c = h['Close'].dropna().tolist()
            if len(c) >= 20:
                mkt['quotes'][t] = round(float(c[-1]), 2)
                s50 = round(sum(c[-50:])/min(50,len(c)), 2)
                s200 = round(sum(c[-200:])/min(200,len(c)), 2)
                s150 = round(sum(c[-150:])/150.0, 2) if len(c)>=150 else 0
                mkt['ma'][t] = [s50, s200, s150]
        except Exception as e:
            print(t, e)
    mkt['asOf'] = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(st, ensure_ascii=False, indent=2), 'utf-8')
if __name__ == '__main__':
    main()