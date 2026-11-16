import json
from common import chart, now, rsi

U = """RELIANCE TCS HDFCBANK ICICIBANK INFY BHARTIARTL SBIN ITC LT HINDUNILVR KOTAKBANK AXISBANK
BAJFINANCE MARUTI SUNPHARMA TITAN NTPC ONGC POWERGRID TATASTEEL ULTRACEMCO ASIANPAINT WIPRO HCLTECH
ADANIENT ADANIPORTS COALINDIA JSWSTEEL TECHM NESTLEIND BAJAJFINSV GRASIM CIPLA DRREDDY EICHERMOT
HINDALCO BPCL INDUSINDBK APOLLOHOSP ETERNAL TRENT BEL HAL""".split()

mom, osd = [], []
for s in U:
    r = chart(s + ".NS", "3mo")
    if not r: continue
    q = r["indicators"]["quote"][0]
    d = [(c, v) for c, v in zip(q["close"], q["volume"]) if c is not None and v]
    if len(d) < 51: continue
    c = [x[0] for x in d]; v = [x[1] for x in d]
    p = c[-1]; s20 = sum(c[-20:]) / 20; s50 = sum(c[-50:]) / 50
    rs = rsi(c); vx = v[-1] / (sum(v[-21:-1]) / 20); ch5 = (p / c[-6] - 1) * 100
    sc = int(p > s20) + int(s20 > s50) + int(50 <= rs <= 70) + int(vx >= 1.5) + int(ch5 > 0)
    row = {"s": s, "price": round(p, 2), "rsi": rs, "volx": round(vx, 1), "ch5": round(ch5, 1), "score": sc}
    if sc >= 4: mom.append(row)
    if rs < 30: osd.append(row)
mom.sort(key=lambda x: -x["score"])
json.dump({"time": now().strftime("%d %b %H:%M IST"), "momentum": mom[:8], "oversold": osd[:5]},
          open("screen.json", "w"))
