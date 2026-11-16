import json, os, time
from common import ai, now, ntfy, mail

kind = "morning" if now().hour < 12 else "close"
N = json.load(open("news.json")); P = json.load(open("prices.json"))
try: S = json.load(open("screen.json"))
except: S = {}
hrs = 16 if kind == "morning" else 9
items = sorted([x for x in N if x.get("ts", 0) > time.time() - hrs * 3600 and x.get("score", 0) >= 5],
               key=lambda x: -x["score"])[:25]
hl = "\n".join(f"{h['symbol']}: price {h['price']}, day {h['pct']}%, P&L {h['pnl']} ({h['pnl_pct']}%)"
               for h in P["holdings"] if not h.get("error"))
mk = ", ".join(f"{k} {v['price']} ({v['pct']}%)" for k, v in P["market"].items())
c = P.get("crude")
cl = (f"Brent ${c['price']} ({c['pct']}% day), trend {c['trend']}, bias {c['bias']}, RSI {c['rsi']}, "
      f"pivot {c['pivot']}, R1 {c['r1']}, R2 {c['r2']}, S1 {c['s1']}, S2 {c['s2']}") if c else "n/a"
sc = ", ".join(f"{x['s']} (RSI {x['rsi']}, vol {x['volx']}x)" for x in S.get("momentum", [])) or "none"
news = "\n".join(f"- [{x['stock']}] {x['title']} ({x['sentiment']}, {x['score']}/10)" for x in items) or "none"
title = "MORNING BRIEF" if kind == "morning" else "POST-MARKET SUMMARY"
prompt = f"""Write a {title} for an Indian trader. Use ONLY the data below. Never invent numbers, events or prices.
Max 250 words. Plain text, short lines, these sections:
1) MARKET: 2 lines from the market data.
2) BRENT: direction, key levels, what to watch (use the given levels only).
3) HOLDINGS: only holdings with news or a move above 2%. One line each: what happened, impact.
4) IDEAS: from the screener list and headlines only. Say why in one line each.
5) AVOID / CAUTION: only if headlines support it.
End with: "Ideas from data, not advice."
MARKET: {mk}
BRENT: {cl}
HOLDINGS:
{hl}
SCREENER MOMENTUM: {sc}
NEWS:
{news}"""
text = ai(prompt)
if not text: raise SystemExit("AI failed")
json.dump({"kind": kind, "time": now().strftime("%d %b %H:%M IST"), "text": text}, open("brief.json", "w"))
ntfy(title.title() + " ready", text[:1500], prio="default")
mail(title.title(), text)
