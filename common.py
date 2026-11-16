import os, time, smtplib, requests, datetime as dt
from email.message import EmailMessage

IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
def now(): return dt.datetime.now(IST)

def chart(sym, rng, itv="1d"):
    for _ in range(3):
        try:
            r = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}",
                params={"range": rng, "interval": itv},
                headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
            return r.json()["chart"]["result"][0]
        except Exception: time.sleep(2)
    return None

def rsi(c, n=14):
    if len(c) < n + 1: return None
    g = l = 0
    for i in range(-n, 0):
        d = c[i] - c[i-1]
        if d > 0: g += d
        else: l -= d
    return 100 if l == 0 else round(100 - 100 / (1 + g / l), 1)

def ntfy(title, msg, link=None, prio="default"):
    t = os.environ.get("NTFY_TOPIC")
    if not t: return
    h = {"Title": title.encode("ascii", "ignore").decode(), "Priority": prio}
    if link: h["Click"] = link
    try: requests.post(f"https://ntfy.sh/{t}", data=msg.encode(), headers=h, timeout=15)
    except Exception as e: print("ntfy fail", e)

def mail(subj, body):
    if not os.environ.get("GMAIL_USER"): return
    try:
        m = EmailMessage()
        m["Subject"], m["From"], m["To"] = subj, os.environ["GMAIL_USER"], os.environ["MAIL_TO"]
        m.set_content(body)
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
            s.login(os.environ["GMAIL_USER"], os.environ["GMAIL_APP_PASS"])
            s.send_message(m)
    except Exception as e: print("mail fail", e)

def groq_models():
    try:
        r = requests.get("https://api.groq.com/openai/v1/models",
            headers={"Authorization": "Bearer " + os.environ["GROQ_API_KEY"]}, timeout=20)
        ids = [m["id"] for m in r.json()["data"]]
    except Exception as e:
        print("model list fail", e); return []
    bad = ("whisper", "guard", "tts", "playai", "orpheus", "embed", "safeguard")
    ids = [i for i in ids if not any(b in i for b in bad)]
    pref = ["gpt-oss-120b", "llama-3.3-70b", "llama-4", "kimi", "qwen", "gpt-oss-20b", "llama-3.1-8b"]
    def rank(i):
        for n, p in enumerate(pref):
            if p in i: return n
        return 99
    ids = sorted(ids, key=rank)[:5]
    print("models to try:", ids)
    return ids

def ai(prompt, js=False):
    for m in groq_models():
        for use_json in ((True, False) if js else (False,)):
            try:
                body = {"model": m, "temperature": 0, "messages": [{"role": "user", "content": prompt}]}
                if use_json: body["response_format"] = {"type": "json_object"}
                r = requests.post("https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": "Bearer " + os.environ["GROQ_API_KEY"]}, json=body, timeout=90)
                if r.status_code == 200:
                    t = r.json()["choices"][0]["message"]["content"]
                    if js:
                        a, b = t.find("{"), t.rfind("}")
                        if a >= 0 and b > a: t = t[a:b+1]
                    return t
                print("AI", m, r.status_code, r.text[:200])
            except Exception as e: print("AI err", m, e)
    return None
