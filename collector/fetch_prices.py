# -*- coding: utf-8 -*-
"""Travelpayouts Data API에서 노선별 최저가를 수집해 SQLite에 저장.

사용: python collector/fetch_prices.py
토큰: 환경변수 TP_TOKEN 또는 프로젝트 루트 .env 파일의 TP_TOKEN=...
"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config
import db

API = "https://api.travelpayouts.com/aviasales/v3/prices_for_dates"


def load_token():
    token = os.environ.get("TP_TOKEN")
    if token:
        return token
    env_file = Path(__file__).resolve().parent.parent / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("TP_TOKEN="):
                return line.split("=", 1)[1].strip()
    raise SystemExit("TP_TOKEN이 없습니다. .env 파일 또는 환경변수로 설정하세요.")


def fetch_route(token, origin, dest):
    params = urllib.parse.urlencode({
        "origin": origin, "destination": dest,
        "currency": config.CURRENCY, "limit": 100,
        "sorting": "price", "one_way": "false",
    })
    req = urllib.request.Request(f"{API}?{params}",
                                 headers={"X-Access-Token": token})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode()).get("data", [])


def main():
    token = load_token()
    conn = db.connect()
    today = date.today().isoformat()
    total = 0
    for origin, dest in config.ROUTES:
        try:
            rows = fetch_route(token, origin, dest)
        except Exception as e:
            print(f"  {origin}-{dest}: 수집 실패 ({e})")
            continue
        for r in rows:
            conn.execute(
                """INSERT OR IGNORE INTO offers
                   (fetched_date, origin, destination, depart_date, return_date,
                    price, airline, transfers, return_transfers, link)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (today, origin, dest,
                 r.get("departure_at", "")[:10], (r.get("return_at") or "")[:10],
                 r.get("price"), r.get("airline"),
                 r.get("transfers"), r.get("return_transfers"),
                 "https://www.aviasales.com" + r.get("link", "")))
        total += len(rows)
        print(f"  {origin}-{dest}: {len(rows)}건")
        time.sleep(0.3)  # rate limit(200/h/IP) 여유
    conn.commit()
    conn.close()
    print(f"완료: {total}건 수집 ({today})")


if __name__ == "__main__":
    main()
