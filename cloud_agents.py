import json, os, yfinance as yf
from datetime import datetime, timezone
from pathlib import Path
STATE_PATH = Path('data/state.json')
CORE = ['PLTR','GOOG','NVDA','NOW','GEV','NBIS','TSM','AVGO','ALAB','LLY','MELI','SPOT','RKLB','SOFI','SPY','AMZN','MA','DASH','CRWD','ISRG']
def extract_youtube_transcripts(st):
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        import requests
    except ImportError:
        return

    yt_key = os.environ.get('YOUTUBE_API_KEY')
    if not yt_key:
        return

    try:
        # Check if Micha.Stocks exists in sources
        sources = st.get('sources', [])
        micha_src = next((s for s in sources if s.get('identifier') == '@Micha.Stocks' and s.get('enabled')), None)
        if not micha_src:
            return

        # Simplified simulation of the extraction flow with try/except
        q = micha_src['identifier'].replace('@', '')
        ch_res = requests.get(f"https://www.googleapis.com/youtube/v3/search?part=snippet&q={q}&type=channel&maxResults=1&key={yt_key}").json()
        channel_id = ch_res.get('items', [{}])[0].get('id', {}).get('channelId')

        if channel_id:
            v_res = requests.get(f"https://www.googleapis.com/youtube/v3/search?part=snippet,id&channelId={channel_id}&order=date&maxResults=2&type=video&key={yt_key}").json()
            for item in v_res.get('items', []):
                vid = item.get('id', {}).get('videoId')
                if vid:
                    try:
                        transcript = YouTubeTranscriptApi.get_transcript(vid, languages=['he', 'en'])
                        # Just a placeholder for actual extraction logic which is handled in frontend
                        pass
                    except Exception as e:
                        print(f"Transcript error for {vid}: {e}")
    except Exception as e:
        print(f"YouTube Agent Error: {e}")

def safe_gemini_parse(text):
    try:
        clean = text.strip()
        clean = clean.replace('```json', '').replace('```', '').strip()
        first = clean.find('{')
        last = clean.rfind('}')
        if first != -1 and last > first:
            clean = clean[first:last+1]
        return json.loads(clean)
    except Exception as e:
        print(f"Gemini parse error: {e}")
        return None

def compute_exact_sma(closes, window):
    valid_closes = [c for c in closes if isinstance(c, (int, float)) and c > 0 and c == c]
    if len(valid_closes) < window:
        return None
    return round(sum(valid_closes[-window:]) / window, 2)

def main():
    try:
        text_content = STATE_PATH.read_text('utf-8')
        st = safe_gemini_parse(text_content) if STATE_PATH.exists() and text_content else {}
    except Exception as e:
        print(f"Error loading state: {e}")
        st = {}

    mkt = st.setdefault('mkt', {'quotes':{}, 'ma':{}, 'targets':{}})

    # Do not overwrite quotes to protect manual static quotes provided by user
    quotes_frozen = {k: v for k, v in mkt.get('quotes', {}).items()}

    success_count = 0

    # Run market agent
    try:
        df = yf.download(CORE, period='1y', interval='1d', auto_adjust=False, progress=False)
        closes = df['Close'] if 'Close' in df else None
    except Exception as e:
        print(f"YF batch download error: {e}")
        closes = None

    if closes is not None:
        for t in CORE:
            try:
                if t not in closes.columns:
                    continue
                c = closes[t].dropna().tolist()

                if not c or c[-1] <= 0:
                    continue

                if t not in quotes_frozen:
                    mkt['quotes'][t] = round(float(c[-1]), 2)

                s50 = compute_exact_sma(c, 50)
                s200 = compute_exact_sma(c, 200)
                s150 = compute_exact_sma(c, 150)

                mkt['ma'][t] = [s50, s200, s150]
                success_count += 1
            except Exception as e:
                print(f"YF error for {t}: {e}")

    # Restore frozen quotes (to not overwrite)
    mkt['quotes'].update(quotes_frozen)

    now_str = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    mkt['lastAttemptAt'] = now_str
    if success_count > 0:
        mkt['asOf'] = now_str
        mkt['lastSuccessAt'] = now_str

    # Run youtube agent
    extract_youtube_transcripts(st)

    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(st, ensure_ascii=False, indent=2), 'utf-8')
if __name__ == '__main__':
    main()