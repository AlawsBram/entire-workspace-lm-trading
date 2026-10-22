#!/usr/bin/env python3
"""
devtools_inspection.py — replicates the browser DevTools panels headlessly on the
live BTC 5m event page and dumps everything a human inspector would see:

  Application: cookies, localStorage, sessionStorage, IndexedDB (names+stores),
               service workers, web manifest
  Network:     every request URL by resource type during ~30s of a live round,
               plus websocket URLs
  Sources:     the JS bundle list (bundles scanned separately for hidden strings)

Output: ui_lab/inspection/*.json
"""
import asyncio, json, time, os
from playwright.async_api import async_playwright

HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "inspection")
os.makedirs(HERE, exist_ok=True)
T = 300

captured = []   # (resource_type, url)
ws_urls = []

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(headless=True)
        ctx = await b.new_context(
            viewport={"width": 1440, "height": 900}, locale="en-US",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36")
        pg = await ctx.new_page()
        pg.on("request", lambda r: captured.append((r.resource_type, r.url)))
        pg.on("websocket", lambda w: ws_urls.append(w.url))
        now = int(time.time()); start = int(now // T) * T
        url = f"https://polymarket.com/event/btc-updown-5m-{start}"
        print("opening", url)
        await pg.goto(url, wait_until="domcontentloaded", timeout=60000)
        await pg.wait_for_timeout(30000)   # let the live page do everything it does

        ls = await pg.evaluate("Object.fromEntries(Object.entries(localStorage))")
        ss = await pg.evaluate("Object.fromEntries(Object.entries(sessionStorage))")
        idb = await pg.evaluate("""async () => {
          const dbs = await indexedDB.databases();
          const out = {};
          for (const d of dbs) {
            try {
              const db = await new Promise((res, rej) => {
                const q = indexedDB.open(d.name);
                q.onsuccess = () => res(q.result); q.onerror = () => rej(q.error);
              });
              const stores = [...db.objectStoreNames];
              const detail = {};
              for (const s of stores) {
                try {
                  detail[s] = await new Promise((res, rej) => {
                    const tx = db.transaction(s, "readonly").objectStore(s);
                    const c = tx.count(); c.onsuccess = () => res(c.result); c.onerror = () => rej();
                  });
                } catch (e) { detail[s] = -1; }
              }
              out[d.name] = detail; db.close();
            } catch (e) { out[d.name] = "ERR"; }
          }
          return out;
        }""")
        sw = [w.url for w in ctx.service_workers]
        cookies = await ctx.cookies()
        manifest_url = await pg.evaluate("(document.querySelector('link[rel=manifest]')||{}).href || null")
        manifest = None
        if manifest_url:
            try:
                import urllib.request
                manifest = json.loads(urllib.request.urlopen(manifest_url, timeout=10).read().decode())
            except Exception as e:
                manifest = f"ERR {e}"
        await b.close()

    def dump(name, obj):
        with open(os.path.join(HERE, name), "w") as f: json.dump(obj, f, indent=1)
        print(f"wrote {name}")

    dump("cookies.json", cookies)
    dump("localstorage.json", ls)
    dump("sessionstorage.json", ss)
    dump("indexeddb.json", idb)
    dump("service_workers.json", sw)
    dump("manifest.json", manifest)
    dump("websockets.json", ws_urls)
    by_type = {}
    for t, u in captured: by_type.setdefault(t, []).append(u)
    dump("network_by_type.json", {k: sorted(set(v)) for k, v in by_type.items()})
    dump("network_all.json", [{"type": t, "url": u} for t, u in captured])
    print(f"requests={len(captured)} cookies={len(cookies)} idbs={len(idb)} sw={len(sw)} ws={len(ws_urls)}")

asyncio.run(main())
