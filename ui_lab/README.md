# UI LAB — read the actual Polymarket UI, compare with the APIs

`ui_api_comparator.py` opens the real event page in headless Chromium, reads the
DOM the user sees (`span.pk-animated-label__text` = Current Price, Up/Down ¢
labels, Price To Beat), and on the same clock records RTDS (Chainlink spot,
60s TWAP) + the CLOB book. One CSV per round:
`ui_vs_api_5m_{round_start}.csv`, plus a RESOLUTION row comparing
official gamma outcome vs our TWAP reconstruction.

Run one cycle manually: `./run_ui_lab.sh` runs forever (one round per cycle);
or `python3 ui_api_comparator.py` for a single round.

VPS: unpack to /opt/ui_lab, `sudo cp deploy/ui-lab.service /etc/systemd/system/`,
`systemctl enable --now ui-lab`. First run downloads Chromium (~120 MB, one time).

Findings from the first audited round: **UI-VS-API-FINDINGS.md**
(Current Price = rounded TWAP; Price To Beat = our open ref; odds labels lag
the book by 2–13¢; display rounds to cents while settlement is full precision).
