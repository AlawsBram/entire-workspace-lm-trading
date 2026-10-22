#!/usr/bin/env python3
"""
ui_api_comparator.py — reads the ACTUAL Polymarket UI DOM in a headless browser
and, on the same clock, the raw API feeds; writes one CSV per 5m round.

WHAT IT CAPTURES (every UI change, ~4 Hz max):
  UI side  : Current Price span (pk-animated-label__text), Up/Down ¢ labels,
             Price To Beat (the open print the UI shows), page result text
  API side : RTDS chainlink spot, RTDS 60s TWAP (the settlement feed),
             RTDS exchange spot (crypto_prices — what the UI is likely fed by),
             CLOB best bid/ask of the Up token

WHY: the UI displays rounded, possibly stale, possibly differently-sourced
numbers. This tool measures the gap: rounding (cents), staleness (which API
series the UI price tracks), odds mispricing (UI ¢ vs CLOB book), and finally
UI-shown resolution vs official gamma resolution vs our own TWAP reconstruction.

CSV: ui_vs_api_5m_{round_start}.csv
No credentials. Public endpoints + public website only.
"""
import asyncio, json, re, time, os, csv, math
import urllib.request
from datetime import datetime, timezone
from collections import deque

import websockets
from playwright.async_api import async_playwright

RTDS = "wss://ws-live-data.polymarket.com"
HERE = os.path.dirname(os.path.abspath(__file__))
SYMBOL = "btc/usd"
T = 300

def log(m): print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}Z] {m}", flush=True)

def hj(u):
    req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode())

class Feeds:
    def __init__(self):
        self.chainlink = None; self.twap = None; self.exchange = None
        self.ts_cl = None; self.ts_tw = None; self.ts_ex = None
        self.samples = deque(maxlen=1500)
        self.o_twap = None; self.acc = 0.0; self.elapsed = 0.0; self.last_ts = None

feeds = Feeds()

def on_feed(topic, obs_ts, val):
    if topic == "crypto_prices_chainlink":
        feeds.chainlink, feeds.ts_cl = val, obs_ts
    elif topic == "crypto_prices_twap_sixty":
        prev, prev_ts = feeds.twap, feeds.ts_tw
        feeds.twap, feeds.ts_tw = val, obs_ts
        feeds.samples.append((obs_ts, val))
        start = int(obs_ts // T) * T
        if feeds.o_twap is None and (obs_ts - start) <= 3:
            feeds.o_twap = val
            log(f"open ref snapped at bell: {val:.2f}")
        if prev is not None:
            t0 = max(prev_ts or obs_ts, start); t1 = min(obs_ts, start + T)
            if t1 > t0:
                feeds.acc += prev * (t1 - t0); feeds.elapsed += (t1 - t0)

async def rtds_loop():
    backoff = 2
    while True:
        try:
            async with websockets.connect(RTDS, max_size=None) as ws:
                log("RTDS connected (3 topics)")
                await ws.send(json.dumps({"action": "subscribe", "subscriptions": [
                    {"topic": t, "type": "update",
                     "filters": json.dumps({"symbol": SYMBOL}, separators=(",", ":"))}
                    for t in ("crypto_prices_chainlink", "crypto_prices_twap_sixty", "crypto_prices")] }))
                backoff = 2
                async def hb():
                    while True:
                        await asyncio.sleep(5); await ws.send("PING")
                hbt = asyncio.create_task(hb())
                async for raw in ws:
                    try: msg = json.loads(raw)
                    except Exception: continue
                    if msg.get("type") != "update": continue
                    p = msg.get("payload", {})
                    if p.get("symbol") != SYMBOL: continue
                    try:
                        val = float(p["full_accuracy_value"]) / 1e18 if "full_accuracy_value" in p else float(p["value"])
                    except Exception: continue
                    on_feed(msg.get("topic", ""), p.get("timestamp", time.time() * 1000) / 1000.0, val)
        except Exception as e:
            log(f"RTDS err {e}; retry {backoff}s"); await asyncio.sleep(backoff); backoff = min(backoff * 2, 60)

async def clob_book(loop, start):
    """best bid/ask of Up token, via executor (blocking urllib ok at 1Hz)"""
    try:
        m = await loop.run_in_executor(None, hj,
            f"https://gamma-api.polymarket.com/markets?slug=btc-updown-5m-{start}")
        tok = json.loads(m[0]["clobTokenIds"])[0]
        b = await loop.run_in_executor(None, hj, f"https://clob.polymarket.com/book?token_id={tok}")
        bb = max((float(x["price"]) for x in b["bids"]), default=None)
        ba = min((float(x["price"]) for x in b["asks"]), default=None)
        return bb, ba
    except Exception:
        return None, None

DOM_SNIPPET = """() => {
  const spans = [...document.querySelectorAll('span.pk-animated-label__text')].map(e=>e.textContent.trim());
  const body = document.body.innerText;
  const ptb = (body.match(/Price To Beat\\n?\\$?([\\d,.]+)/) || [])[1] || null;
  const res = (body.match(/(Resolved[^\\n]{0,40}|This market resolved[^\\n]{0,40}|"[UD]p"[^\\n]{0,60})/i) || [])[1] || null;
  const price = spans.find(s => s.startsWith('$') && s.includes(',')) || null;
  const cents = spans.filter(s => s.endsWith('¢'));
  return { price, up: cents[0]||null, down: cents[1]||null, ptb, res,
           live_btn: [...document.querySelectorAll('a,button')].some(e=>/go to live market/i.test(e.textContent||'')) };
}"""

async def main():
    now = time.time()
    start = (int(now // T) + 1) * T          # NEXT bell: record the full next window
    log(f"waiting for bell {start} ({datetime.fromtimestamp(start, timezone.utc):%H:%M:%S}Z); recording full round")
    while time.time() < start - 4:
        await asyncio.sleep(1)
    loop = asyncio.get_running_loop()
    asyncio.create_task(rtds_loop())
    csv_path = os.path.join(HERE, f"ui_vs_api_5m_{start}.csv")
    cols = ["ts_unix","ts_iso","t_into_round_s","ui_current_price","ui_current_price_num",
            "ui_up_cents","ui_down_cents","ui_price_to_beat","api_chainlink_spot","api_twap60",
            "api_exchange_spot","clob_up_bid","clob_up_ask","ui_minus_chainlink","ui_minus_exchange",
            "ui_minus_twap","ui_up_minus_bid","ui_up_minus_ask","ui_live_btn","ui_result_text"]
    f = open(csv_path, "w", newline=""); w = csv.writer(f); w.writerow(cols)
    book = {"bb": None, "ba": None}
    async def book_poller():
        while time.time() < start + T + 20:
            bb, ba = await clob_book(loop, start)
            book["bb"], book["ba"] = bb, ba
            await asyncio.sleep(1.0)
    asyncio.create_task(book_poller())

    async with async_playwright() as p:
        b = await p.chromium.launch(headless=True)
        pg = await b.new_page(viewport={"width":1440,"height":900}, locale="en-US",
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36")
        url = f"https://polymarket.com/event/btc-updown-5m-{start}"
        log(f"opening {url}")
        await pg.goto(url, wait_until="domcontentloaded", timeout=60000)
        last = None; rows = 0; last_book_log = 0
        end = start + T + 25
        while time.time() < end:
            now = time.time()
            try:
                d = await pg.evaluate(DOM_SNIPPET)
            except Exception:
                await asyncio.sleep(0.5); continue
            key = (d["price"], d["up"], d["down"], d.get("res"))
            if key != last or (rows and int(now) % 4 == 0 and now - last_book_log > 4):
                last = key; last_book_log = now
                def num(x):
                    try: return float(x.replace("$","").replace(",","").replace("¢",""))
                    except Exception: return None
                upn, ptn = num(d["up"]), num(d["price"])
                upc = upn / 100 if upn is not None else None
                row = [round(now,3), datetime.fromtimestamp(now, timezone.utc).strftime("%H:%M:%S.%f")[:-3],
                       round(now - start,1), d["price"], ptn, d["up"], d["down"], d["ptb"],
                       feeds.chainlink, feeds.twap, feeds.exchange, book["bb"], book["ba"],
                       round(ptn - feeds.chainlink,2) if (ptn and feeds.chainlink) else "",
                       round(ptn - feeds.exchange,2) if (ptn and feeds.exchange) else "",
                       round(ptn - feeds.twap,2) if (ptn and feeds.twap) else "",
                       round(upc - book["bb"],3) if (upc and book["bb"]) else "",
                       round(upc - book["ba"],3) if (upc and book["ba"]) else "",
                       d["live_btn"], d["res"]]
                w.writerow(row); f.flush(); rows += 1
            await asyncio.sleep(0.25)
        # final resolution capture: UI text + official + our reconstruction
        try: final_ui = await pg.evaluate("document.body.innerText.slice(0,2000)")
        except Exception: final_ui = ""
        await b.close()
    settled = None
    for _ in range(24):
        try:
            m = hj(f"https://gamma-api.polymarket.com/events?slug=btc-updown-5m-{start}")[0]["markets"][0]
            pr = [float(x) for x in json.loads(m["outcomePrices"])]
            if m.get("closed") or not m.get("acceptingOrders") or pr[0] >= 0.9995 or pr[0] <= 0.0005:
                settled = "Up" if pr[0] > 0.5 else "Down"; break
        except Exception: pass
        await asyncio.sleep(20)
    acc_avg = feeds.acc / feeds.elapsed if feeds.elapsed else None
    ours = ("Up" if acc_avg >= feeds.o_twap else "Down") if (acc_avg and feeds.o_twap) else None
    ui_says = "Up" if re.search(r'resolved[^"\n]*"?\s*Up|Up\s+won|"Up"', final_ui or "", re.I) else \
              ("Down" if re.search(r'resolved[^"\n]*"?\s*Down|Down\s+won|"Down"', final_ui or "", re.I) else None)
    with open(csv_path, "a", newline="") as f:
        w = csv.writer(f)
        w.writerow(["RESOLUTION", "", "", "", "", "", "", f"ui_ptb={feeds.o_twap}",
                    "", f"our_acc_avg={acc_avg:.2f}" if acc_avg else "", "", "", "",
                    "", "", "", "", "",
                    f"official={settled} ui={ui_says} ours={ours} agree={settled==ours}"])
    log(f"DONE rows={rows} official={settled} ui_shows={ui_says} our_reconstruction={ours} csv={csv_path}")

if __name__ == "__main__":
    asyncio.run(main())
