# -*- coding: utf-8 -*-
"""축적된 가격 데이터에서 특가를 판정.

판정 기준: 같은 노선·같은 유형(직항/경유)의 최근 BASELINE_DAYS일
가격 중앙값 대비 DEAL_RATIO 이하. 직항과 경유는 시세가 다르므로 분리 계산.
사용: python collector/detect_deals.py  (build_site.py에서도 import)
"""
import statistics
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config
import db

# 왕복 모두 경유 0회면 직항으로 분류
IS_DIRECT_SQL = "(transfers=0 AND IFNULL(return_transfers,0)=0)"


def compute_deals(conn):
    """오늘 수집분 중 특가 목록을 dict 리스트로 반환 (할인율 내림차순)."""
    today = date.today().isoformat()
    since = (date.today() - timedelta(days=config.BASELINE_DAYS)).isoformat()
    deals = []
    for origin, dest in config.ROUTES:
        for is_direct in (1, 0):
            cond = IS_DIRECT_SQL if is_direct else f"NOT {IS_DIRECT_SQL}"
            prices = [p for (p,) in conn.execute(
                f"""SELECT price FROM offers
                    WHERE origin=? AND destination=? AND fetched_date>=? AND {cond}""",
                (origin, dest, since))]
            if len(prices) < config.MIN_SAMPLES:
                continue
            median = statistics.median(prices)
            threshold = median * config.DEAL_RATIO
            rows = conn.execute(
                f"""SELECT depart_date, return_date, price, airline,
                           transfers, IFNULL(return_transfers,0), link
                    FROM offers
                    WHERE origin=? AND destination=? AND fetched_date=?
                          AND {cond} AND price<=?
                    ORDER BY price LIMIT 3""",
                (origin, dest, today, threshold)).fetchall()
            for depart, ret, price, airline, t_out, t_back, link in rows:
                deals.append({
                    "origin": origin, "destination": dest,
                    "depart_date": depart, "return_date": ret,
                    "price": price, "airline": airline,
                    "is_direct": bool(is_direct),
                    "transfers": t_out, "return_transfers": t_back,
                    "discount_pct": round((1 - price / median) * 100),
                    "median": int(median), "link": link,
                })
    deals.sort(key=lambda d: -d["discount_pct"])
    return deals


def main():
    conn = db.connect()
    deals = compute_deals(conn)
    conn.close()
    today = date.today().isoformat()
    if not deals:
        print(f"[{today}] 특가 없음 (기준: 유형별 시세 중앙값의 {int(config.DEAL_RATIO*100)}% 이하)")
        return
    print(f"[{today}] 특가 {len(deals)}건 발견")
    for d in deals:
        kind = "직항" if d["is_direct"] else \
            f"경유(가는편 {d['transfers']}회/오는편 {d['return_transfers']}회)"
        print(f"  {d['origin']}→{d['destination']} {d['depart_date']}~{d['return_date']} "
              f"{d['price']:,}원 ({d['airline']}, {kind}) "
              f"— 동일 유형 시세 {d['median']:,}원 대비 {d['discount_pct']}% 저렴")
        print(f"    {d['link']}")


if __name__ == "__main__":
    main()
