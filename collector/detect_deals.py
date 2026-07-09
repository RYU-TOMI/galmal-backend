# -*- coding: utf-8 -*-
"""축적된 가격 데이터에서 특가를 판정해 리포트 출력.

판정 기준: 같은 노선·같은 유형(직항/경유)의 최근 BASELINE_DAYS일
가격 중앙값 대비 DEAL_RATIO 이하. 직항과 경유는 시세가 다르므로 분리 계산.
사용: python collector/detect_deals.py
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


def main():
    conn = db.connect()
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
                kind = "직항" if is_direct else f"경유(가는편 {t_out}회/오는편 {t_back}회)"
                deals.append((origin, dest, depart, ret, price, airline, kind,
                              round((1 - price / median) * 100), int(median), link))
    conn.close()

    if not deals:
        print(f"[{today}] 특가 없음 (기준: 유형별 시세 중앙값의 {int(config.DEAL_RATIO*100)}% 이하)")
        return
    deals.sort(key=lambda d: -d[7])
    print(f"[{today}] 특가 {len(deals)}건 발견")
    for origin, dest, depart, ret, price, airline, kind, disc, median, link in deals:
        print(f"  {origin}→{dest} {depart}~{ret} {price:,}원 ({airline}, {kind}) "
              f"— 동일 유형 시세 {median:,}원 대비 {disc}% 저렴")
        print(f"    {link}")


if __name__ == "__main__":
    main()
