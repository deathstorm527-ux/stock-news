import json, time
from common import chart, now, ntfy, rsi

H = json.load(open("watchlist.json"))["holdings"]
rd = lambda x: None if x is None else round(x, 2)

def quote(sym, rng="3mo"):
    r = chart(sym, rng)
    if not r: return None
    q = r["indicators"]["quote"][0]
    rows = [(c, h, l) for c, h, l in zip(q["close"], q["high"], q["low"]) if None not in (c, h, l)]
    if len(rows) < 2: return None
    p = r["meta"].get("regularMarketPrice") or rows[-1][0]
    pv = rows[-2][0]
    return {"price": p, "prev": pv, "chg": p - pv, "pct": (p - pv) / pv * 100, "rows": rows}

hold, ti, tv, td = [], 0, 0, 0
for s in H:
    q = quote(s["symbol"] + ".NS") or quote(s["symbol"] + ".BO")
    if not q:
        hold.append({"symbol": s["symbol"], "name": s["name"], "error": True}); continue
    inv = s["qty"] * s["avg"]; val = s["qty"] * q["price"]; day = s["qty"] * q["chg"]
    ti += inv; tv += val; td += day
    hold.append({"symbol": s["symbol"], "name": s["name"], "qty": s["qty"], "avg": s["avg"],
        "price": rd(q["price"]), "prev": rd(q["prev"]), "pct": rd(q["pct"]),
        "inv": rd(inv), "val": rd(val), "pnl": rd(val - inv),
        "pnl_pct": rd((val - inv) / inv * 100), "day": rd(day)})

M = {"NIFTY": "^NSEI", "SENSEX": "^BSESN", "INDIA VIX": "^INDIAVIX",
     "USD/INR": "INR=X", "GOLD": "GC=F", "WTI": "CL=F"}
market = {}
for k, v in M.items():
    q = quote(v, "1mo")
    if q: market[k] = {"price": rd(q["price"]), "pct": rd(q["pct"])}

crude = None
b = quote("BZ=F", "6mo")
if b:
    c = [x[0] for x in b["rows"]]
    p = b["price"]
    s20 = sum(c[-20:]) / min(20, len(c)); s50 = sum(c[-50:]) / min(50, len(c))
    trend = "UP" if p > s20 > s50 else "DOWN" if p < s20 < s50 else "SIDEWAYS"
    pc, ph, pl = b["rows"][-2]
    piv = (ph + pl + pc) / 3
    r1, s1, r2, s2 = 2*piv - pl, 2*piv - ph, piv + (ph - pl), piv - (ph - pl)
    rs = rsi(c)
    ir = chart("BZ=F", "1d", "5m"); sp, hi, lo, mv = [], None, None, None
    if ir:
        sp = [x for x in ir["indicators"]["quote"][0]["close"] if x is not None]
        hi = ir["meta"].get("regularMarketDayHigh"); lo = ir["meta"].get("regularMarketDayLow")
        if len(sp) >= 7: mv = (sp[-1] - sp[-7]) / sp[-7] * 100
    sc = (1 if trend == "UP" else -1 if trend == "DOWN" else 0) + (1 if p > piv else -1)
    bias = "BULLISH" if sc >= 2 else "BEARISH" if sc <= -2 else "NEUTRAL"
    note = "Overbought, pullback risk" if rs and rs > 70 else "Oversold, bounce possible" if rs and rs < 30 else "RSI normal"
    crude = {"price": rd(p), "pct": rd(b["pct"]), "trend": trend, "bias": bias, "rsi": rs, "note": note,
        "sma20": rd(s20), "sma50": rd(s50), "pivot": rd(piv), "r1": rd(r1), "r2": rd(r2),
        "s1": rd(s1), "s2": rd(s2), "hi": rd(hi), "lo": rd(lo), "move30": rd(mv),
        "spark": [round(x, 2) for x in sp[-72:]]}

# ---- alerts (each fires once per day, Brent move once per hour) ----
try: st = json.load(open("alert_state.json"))
except: st = {}
today = now().strftime("%Y-%m-%d")
if st.get("date") != today: st = {"date": today, "sent": [], "brent_ts": st.get("brent_ts", 0)}
def once(k):
    if k in st["sent"]: return False
    st["sent"].append(k); return True
if crude:
    p = crude["price"]
    if crude["move30"] is not None and abs(crude["move30"]) >= 1.0 and time.time() - st["brent_ts"] > 3600:
        st["brent_ts"] = time.time()
        ntfy(f"BRENT {crude['move30']:+.1f}% in 30 min", f"Price ${p}. Trend {crude['trend']}, bias {crude['bias']}", prio="high")
    if p > crude["r1"] and once("brent_r1"): ntfy("BRENT above R1", f"${p} broke R1 {crude['r1']}", prio="high")
    if p < crude["s1"] and once("brent_s1"): ntfy("BRENT below S1", f"${p} broke S1 {crude['s1']}", prio="high")
for h in hold:
    if h.get("error"): continue
    if abs(h["pct"]) >= 5 and once(f"{h['symbol']}{'up' if h['pct'] > 0 else 'dn'}"):
        ntfy(f"{h['symbol']} {h['pct']:+.1f}% today", f"Price {h['price']}. P&L {h['pnl']} ({h['pnl_pct']}%)")
json.dump(st, open("alert_state.json", "w"))

json.dump({"updated": now().strftime("%d %b %H:%M IST"),
    "totals": {"inv": rd(ti), "val": rd(tv), "pnl": rd(tv - ti), "day": rd(td)},
    "holdings": hold, "market": market, "crude": crude}, open("prices.json", "w"))
