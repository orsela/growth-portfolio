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
            # Fallback if sources not in state
            micha_src = {'name': 'מיכה סטוקס', 'identifier': '@Micha.Stocks', 'prompt': 'חלץ כל טיקר שהוזכר, מחיר פריצה, מחיר יעד, קו אזהרה וסיכום תמציתי בעברית עד 20 מילה.'}

        # Simplified simulation of the extraction flow with try/except
        q = micha_src['identifier'].replace('@', '')
        ch_res = requests.get(f"https://www.googleapis.com/youtube/v3/search?part=snippet&q={q}&type=channel&maxResults=1&key={yt_key}").json()
        channel_id = ch_res.get('items', [{}])[0].get('id', {}).get('channelId')

        gemini_key = os.environ.get('GEMINI_API_KEY')
        if not gemini_key:
            return

        import google.generativeai as genai
        genai.configure(api_key=gemini_key)
        model = genai.GenerativeModel('gemini-2.5-flash')

        if channel_id:
            v_res = requests.get(f"https://www.googleapis.com/youtube/v3/search?part=snippet,id&channelId={channel_id}&order=date&maxResults=2&type=video&key={yt_key}").json()

            # Init mv array if not exists
            if 'mv' not in st:
                st['mv'] = []

            # Keep track of existing vids
            existing_vids = {v.get('vid') for v in st.get('mv', []) if v.get('vid')}

            for item in v_res.get('items', []):
                vid = item.get('id', {}).get('videoId')
                if vid and vid not in existing_vids:
                    try:
                        transcript_list = YouTubeTranscriptApi.get_transcript(vid, languages=['he', 'en'])
                        full_text = " ".join([t['text'] for t in transcript_list])

                        prompt = f"""
{micha_src.get('prompt', 'חלץ כל טיקר שהוזכר, מחיר פריצה, מחיר יעד, קו אזהרה וסיכום תמציתי בעברית עד 20 מילה.')}
החזר אך ורק מערך JSON תקין שבו כל איבר הוא אובייקט עם השדות:
"t" (string: הטיקר, למשל "PLTR"),
"breakout" (number או null),
"target" (number או null),
"warning" (number או null),
"summary" (string).
אין להוסיף טקסט מעבר ל-JSON.
הנה התמלול:
{full_text}
"""
                        response = model.generate_content(prompt)
                        parsed = safe_gemini_parse(response.text)

                        if isinstance(parsed, list):
                            snippet = item.get('snippet', {})

                            # Prepend the new video to mv array
                            new_mv = {
                                "vid": vid,
                                "source": micha_src.get('name', 'מיכה סטוקס'),
                                "date": snippet.get('publishedAt', '')[:10],
                                "title": snippet.get('title', ''),
                                "url": f"https://www.youtube.com/watch?v={vid}",
                                "rows": parsed
                            }
                            st['mv'].insert(0, new_mv)
                    except Exception as e:
                        print(f"Transcript error for {vid}: {e}")
    except Exception as e:
        print(f"YouTube Agent Error: {e}")

def safe_gemini_parse(text):
    try:
        clean = text.strip()
        clean = clean.replace('```json', '').replace('```', '').strip()
        # Find either array or object
        first_obj = clean.find('{')
        last_obj = clean.rfind('}')
        first_arr = clean.find('[')
        last_arr = clean.rfind(']')

        # Determine if it's an array or object based on first occurrence
        if first_arr != -1 and (first_obj == -1 or first_arr < first_obj):
            if last_arr > first_arr:
                clean = clean[first_arr:last_arr+1]
        elif first_obj != -1:
            if last_obj > first_obj:
                clean = clean[first_obj:last_obj+1]

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
    for t in CORE:
        try:
            h = yf.Ticker(t).history(period='1y', interval='1d', auto_adjust=False)
            c = h['Close'].dropna().tolist()

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