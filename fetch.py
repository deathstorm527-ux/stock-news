import json, os, hashlib, requests, feedparser, smtplib
from email.message import EmailMessage
from urllib.parse import quote

def mail(subj, body):
    m = EmailMessage()
    m["Subject"], m["From"], m["To"] = subj, os.environ["GMAIL_USER"], os.environ["MAIL_TO"]
    m.set_content(body)
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(os.environ["GMAIL_USER"], os.environ["GMAIL_APP_PASS"])
        s.send_message(m)

CFG = json.load(open("watchlist.json"))
H, T = CFG["holdings"], CFG["topics"]
FEEDS = [
 "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
 "https://economictimes.indiatimes.com/markets/stocks/rssfeeds/2146842.cms",
 "https://www.livemint.com/rss/markets",
 "https://www.business-standard.com/rss/markets-106.rss",
 "https://www.moneycontrol.com/rss/business.xml",
 "https://news.google.com/rss/search?q=RBI+OR+SEBI+OR+Sensex+OR+Nifty+when:1d&hl=en-IN&gl=IN&ceid=IN:en",
 "https://news.google.com/rss/search?q=stocks+to+buy+India+when:1d&hl=en-IN&gl=IN&ceid=IN:en",
]
for s in H + T:
    FEEDS.append(f"https://news.google.com/rss/search?q={quote(s['name'])}+when:1d&hl=en-IN&gl=IN&ceid=IN:en")

try: old = json.load(open("news.json"))
except: old = []
seen = {i["id"] for i in old}

new = []
for url in FEEDS:
    try:
        for e in feedparser.parse(url).entries[:12]:
            t = e.title.strip()
            i = hashlib.md5(t.lower().encode()).hexdigest()[:12]
            if i in seen: continue
            seen.add(i)
            new.append({"id": i, "title": t, "link": e.link,
                        "time": e.get("published", ""), "src": url.split("/")[2]})
    except Exception as ex: print("feed fail", url, ex)

new = new[:60]
alerts = []
if new:
    held = "; ".join(f"{s['symbol']} ({s['name']}) qty {s['qty']} avg {s['avg']}" for s in H)
    lines = "\n".join(f"{n}. {x['title']}" for n, x in enumerate(new))
    prompt = f"""You analyse news for an Indian trader.
His holdings: {held}.
He also trades Brent/crude oil intraday (use stock="CRUDE") and cares about gold (stock="GOLD").
RULES: Use ONLY the headlines below. Never invent facts or prices.
Keep a headline only if it affects his holdings, crude oil, gold, the Indian market overall (stock="MARKET"),
or it names another NSE/BSE stock with a clear reason to buy or avoid (use that stock's name as stock).
For each kept headline return: id (number), stock, sentiment ("bullish"/"bearish"/"neutral"),
score (1-10 impact), action ("BUY IDEA"/"AVOID"/"HOLD"/"WATCH"), reason (max 18 words).
For CRUDE, say in the reason whether it points up or down.
Return JSON: {{"results":[...]}}
Headlines:
{lines}"""
    r = requests.post("https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": "Bearer " + os.environ["GROQ_API_KEY"]},
        json={"model": "llama-3.3-70b-versatile", "temperature": 0,
              "response_format": {"type": "json_object"},
              "messages": [{"role": "user", "content": prompt}]}, timeout=60)
    try: res = json.loads(r.json()["choices"][0]["message"]["content"])["results"]
    except Exception as ex: print("AI fail", ex, r.text[:300]); res = []
    topic = os.environ.get("NTFY_TOPIC")
    for a in res:
        try: x = new[int(a["id"])]
        except: continue
        x.update(stock=a["stock"], sentiment=a["sentiment"], score=int(a["score"]),
                 action=a.get("action", "WATCH"), reason=a["reason"])
        old.insert(0, x)
        limit = 6 if x["stock"] == "CRUDE" else 7
        if x["score"] >= limit:
            alerts.append(x)
            if topic:
                icon = "UP" if x["sentiment"] == "bullish" else "DOWN"
                try:
                    requests.post(f"https://ntfy.sh/{topic}",
                        data=(x["action"] + ": " + x["reason"]).encode(),
                        headers={"Title": f"{x['stock']} {icon} {x['score']}/10",
                                 "Click": x["link"]})
                except Exception as ex: print("ntfy fail", ex)

if alerts and os.environ.get("GMAIL_USER"):
    body = "\n\n".join(f"{x['stock']} | {x['action']} | {x['sentiment']} | {x['score']}/10\n{x['reason']}\n{x['link']}" for x in alerts)
    try: mail(f"{len(alerts)} important stock alerts", body)
    except Exception as ex: print("mail fail", ex)

json.dump(old[:400], open("news.json", "w"), indent=1)
