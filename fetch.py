import json, os, time, hashlib, feedparser
from urllib.parse import quote_plus
from common import ai, ntfy, mail

FAST = bool(os.environ.get("FAST"))
CFG = json.load(open("watchlist.json"))
H, T = CFG["holdings"], CFG["topics"]
MIN = {s["symbol"]: s.get("min", 7) for s in H}
G = "https://news.google.com/rss/search?q={}&hl=en-IN&gl=IN&ceid=IN:en"
g = lambda q: G.format(quote_plus(q))

if FAST:
    FEEDS = [g(q + " when:2h") for q in ("Brent crude oil", "OPEC oil supply",
             "crude oil prices Iran OR Russia OR Israel OR Fed")]
    PER, CAP = 8, 25
else:
    FEEDS = [
     "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
     "https://economictimes.indiatimes.com/markets/stocks/rssfeeds/2146842.cms",
     "https://www.livemint.com/rss/markets",
     "https://www.business-standard.com/rss/markets-106.rss",
     "https://www.moneycontrol.com/rss/business.xml",
     g("RBI OR SEBI OR Sensex OR Nifty when:1d"),
     g("stocks to buy India when:1d"),
    ] + [g(s["name"] + " when:1d") for s in H + T]
    PER, CAP = 12, 50

try: old = json.load(open("news.json"))
except: old = []
try: seen_l = json.load(open("seen.json"))
except: seen_l = []
seen = set(seen_l) | {i["id"] for i in old}

new = []
for url in FEEDS:
    try:
        for e in feedparser.parse(url).entries[:PER]:
            t = e.title.strip()
            i = hashlib.md5(t.lower().encode()).hexdigest()[:12]
            if i in seen: continue
            seen.add(i)
            new.append({"id": i, "title": t, "link": e.link, "ts": int(time.time()),
                        "time": e.get("published", ""), "src": url.split("/")[2]})
    except Exception as ex: print("feed fail", url, ex)
new = new[:CAP]

alerts = []
if new:
    held = "; ".join(f"{s['symbol']} ({s['name']}) qty {s['qty']} avg {s['avg']}" for s in H)
    lines = "\n".join(f"{n}. {x['title']}" for n, x in enumerate(new))
    prompt = f"""You analyse news for an Indian trader.
His holdings: {held}.
He trades Brent/crude oil intraday (stock="CRUDE") and cares about gold (stock="GOLD").
RULES: Use ONLY the headlines below. Never invent facts or prices.
For his holdings use the exact SYMBOL given.
Keep a headline only if it affects his holdings, crude oil, gold, the Indian market overall (stock="MARKET"),
or names another NSE/BSE stock with a clear reason to buy or avoid (use that stock's name as stock).
For each kept headline return: id (number), stock, sentiment ("bullish"/"bearish"/"neutral"),
score (1-10 impact), action ("BUY IDEA"/"AVOID"/"HOLD"/"WATCH"), reason (max 18 words).
For CRUDE, say in the reason whether it points up or down.
Return JSON: {{"results":[...]}}
Headlines:
{lines}"""
    try:
        res = json.loads(ai(prompt, True))["results"]
        seen_l += [x["id"] for x in new]
    except Exception as ex: print("AI fail", ex); res = []
    for a in res:
        try: x = new[int(a["id"])]
        except: continue
        x.update(stock=str(a.get("stock", "MARKET")), sentiment=a.get("sentiment", "neutral"),
                 score=int(a.get("score", 0)), action=a.get("action", "WATCH"), reason=a.get("reason", ""))
        old.insert(0, x)
        limit = 6 if x["stock"] == "CRUDE" else MIN.get(x["stock"], 7)
        if x["score"] >= limit:
            alerts.append(x)
            icon = "UP" if x["sentiment"] == "bullish" else "DOWN"
            ntfy(f"{x['stock']} {icon} {x['score']}/10", f"{x['action']}: {x['reason']}",
                 x["link"], "high" if x["score"] >= 9 else "default")

if alerts and not FAST:
    mail(f"{len(alerts)} important stock alerts",
         "\n\n".join(f"{x['stock']} | {x['action']} | {x['sentiment']} | {x['score']}/10\n{x['reason']}\n{x['link']}" for x in alerts))

json.dump(old[:400], open("news.json", "w"), indent=1)
json.dump(seen_l[-4000:], open("seen.json", "w"))
