# -*- coding: utf-8 -*-
"""발견 피드용 광역 수집: 한국 전 공항 → 모든 목적지 최저가 (공항당 1회 호출).

기존 fetch_prices.py(노선별 상세, 30일 히스토리)와 역할이 다르다:
- fetch_prices : 소수 노선을 '깊게' (날짜별) — 노선 상세 페이지·특가 판정용
- fetch_breadth: 전 목적지를 '넓게' (목적지당 최저가 1건) — "어디 갈까" 발견용

v2/prices/latest는 origin 하나로 수백 목적지를 한 번에 준다. 5개 공항 = 5회 호출.
결과는 broad_offers 테이블에 (수집일, 출발, 목적지, 최저가, 신선도...) 저장.

사용: python collector/fetch_breadth.py
"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import db
from dests import ORIGINS, is_destination

API = "https://api.travelpayouts.com/v2/prices/latest"
MAX_AGE_DAYS = 3   # 발견 피드 신선도 기준


def load_token():
    token = os.environ.get("TP_TOKEN")
    if token:
        return token
    env = Path(__file__).resolve().parent.parent / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("TP_TOKEN="):
                return line.split("=", 1)[1].strip()
    raise SystemExit("TP_TOKEN이 없습니다.")


def fetch_origin(token, origin):
    params = urllib.parse.urlencode(dict(
        origin=origin, currency="krw", limit=1000, period_type="year"))
    req = urllib.request.Request(f"{API}?{params}", headers={"X-Access-Token": token})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode()).get("data", [])


def main():
    token = load_token()
    conn = db.connect()
    today = date.today().isoformat()
    now = datetime.now()
    kept = 0
    for origin in ORIGINS:
        try:
            rows = fetch_origin(token, origin)
        except Exception as e:
            print(f"  {origin}: 수집 실패 ({e})")
            continue
        n_origin = 0
        for r in rows:
            dest = r.get("destination")
            if not is_destination(dest):        # 품질 필터: 사전에 있는 목적지만
                continue
            found = r.get("found_at", "")
            try:
                age = (now - datetime.fromisoformat(found)).days
            except (ValueError, TypeError):
                continue
            if age > MAX_AGE_DAYS:               # 신선도 필터
                continue
            conn.execute(
                """INSERT OR REPLACE INTO broad_offers
                   (fetched_date, origin, destination, price, transfers,
                    depart_date, return_date, found_at)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (today, origin, dest, r.get("value"), r.get("number_of_changes"),
                 r.get("depart_date"), r.get("return_date"), found))
            n_origin += 1
            kept += 1
        print(f"  {origin}: {n_origin}건 (신선·인기 목적지)")
        time.sleep(0.5)
    conn.commit()
    conn.close()
    print(f"완료: {kept}건 저장 ({today})")


if __name__ == "__main__":
    main()
