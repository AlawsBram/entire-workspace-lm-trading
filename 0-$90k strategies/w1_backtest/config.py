#!/usr/bin/env python3
"""Q1 W1 backtest — shared config. Pre-registered 2026-10-15, see BACKTEST-QUEUE.md."""
import os, json, math, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
os.makedirs(DATA, exist_ok=True)

# city slug -> (lat, lon, utc_offset_hours)
CITIES = {
    "hong-kong": (22.31, 114.17, 8), "wuhan": (30.59, 114.30, 8),
    "wellington": (-41.29, 174.78, 13), "seoul": (37.57, 126.98, 9),
    "new-york-city": (40.78, -73.97, -4), "chicago": (41.88, -87.63, -5),
    "miami": (25.76, -80.19, -4), "london": (51.51, -0.13, 1),
    "paris": (48.86, 2.35, 2), "tokyo": (35.68, 139.69, 9),
    "singapore": (1.35, 103.82, 8), "sydney": (-33.87, 151.21, 11),
    "dallas": (32.78, -96.80, -5), "atlanta": (33.75, -84.39, -4),
    "denver": (39.74, -104.99, -6), "houston": (29.76, -95.37, -5),
    "los-angeles": (34.05, -118.24, -7), "san-francisco": (37.77, -122.42, -7),
    "seattle": (47.61, -122.33, -7), "phoenix": (33.45, -112.07, -7),
    "boston": (42.36, -71.06, -4), "washington-dc": (38.91, -77.04, -4),
    "toronto": (43.65, -79.38, -4), "madrid": (40.42, -3.70, 2),
    "rome": (41.90, 12.50, 2), "munich": (48.14, 11.58, 2),
    "amsterdam": (52.37, 4.90, 2), "warsaw": (52.23, 21.01, 2),
    "taipei": (25.03, 121.57, 8),
}
WINDOW_START = "2026-09-14"          # backtest window (30d) — pre-registered
LEADS = {"L0": "stitched", "L1": 1, "L2": 2, "L3": 3}   # L0 = same-day short lead
THETAS = (0.10, 0.15, 0.20)
SLIPPAGE = 0.02                      # conservative half-spread added to history mid
MIN_PROB = 0.08                      # candidate filter (model-side only, no lookahead)
MAX_PRICE_AGE_H = 24                 # older carry-forward price = stale, skip pair
SPLIT = 0.6                          # first 60% of days fit bias/sigma, last 40% holdout
SLEEP = 0.25

def hj(url, t=20):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=t) as r:
        return json.loads(r.read().decode())

def save(name, obj):
    json.dump(obj, open(os.path.join(DATA, name), "w"))

def load(name):
    with open(os.path.join(DATA, name)) as f:
        return json.load(f)

def norm_cdf(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))
