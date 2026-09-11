# -*- coding: utf-8 -*-
"""노선 통계 — `offers`에서 창(window)을 잘라 집계한다.

**이 모듈은 커넥션만 받는다.** 파일 경로도, 화면도, 발행 형식도 모른다.
`publish_v1`(v1 JSON)과 `build_site.route_page()`(옛 HTML)가 **같은 함수**를 부르므로
두 경로가 갈릴 수 없다. 이전(M3)이 끝나면 옛 HTML 쪽이 사라지고 여기와 `publish_v1`만 남는다.

왜 따로 떼었나 (M3 T0, 2026-09-11):
  원래 `build_site.py` 안에 있었고 `publish_v1`이 그걸 import했다. **살아남을 쪽이
  사라질 쪽에 얹혀 있던 것**이다(BACKEND.md §11.11). T3에서 `build_site`의 HTML을
  걷어낼 때 통계까지 딸려 흔들리지 않게, 먼저 떼어 둔다.

🔴 **sqlite 전용 SQL은 이 파일에만 있다** — `strftime` 두 곳(`month_min`·`weekday_min`).
나중에 Postgres로 갈 때 고칠 곳이 여기 두 줄이다(`SPLIT.md` §5c 이식 표면).
어댑터를 미리 만들지 않는다. **흩어지지 않게만** 둔다.
"""
from datetime import timedelta

import timeutil
from detect_deals import IS_DIRECT_SQL

# 통계의 **창**. `meta.json`이 이 값을 그대로 싣는다 — 두 곳에 적으면 갈라진다.
WINDOW_DAYS = 30

# 화면은 월요일부터 보여준다. **표시 관례이지 데이터의 성질이 아니다.**
WEEK_ORDER = (1, 2, 3, 4, 5, 6, 0)



def daily_min(conn, origin, dest, days=WINDOW_DAYS, direct_only=None):
    since = (timeutil.today_utc() - timedelta(days=days)).isoformat()
    cond = ""
    if direct_only is True:
        cond = f"AND {IS_DIRECT_SQL}"
    elif direct_only is False:
        cond = f"AND NOT {IS_DIRECT_SQL}"
    return conn.execute(
        f"""SELECT fetched_date, MIN(price) FROM offers
            WHERE origin=? AND destination=? AND fetched_date>=? {cond}
            GROUP BY fetched_date ORDER BY fetched_date""",
        (origin, dest, since)).fetchall()


def month_min(conn, origin, dest, min_samples=3, limit=10):
    """출발월별 (월, 최저가, **표본수**) — **오늘 이후 출발만** 센다 (BB29).

    창이 없으면 이미 지나간 달이 버킷으로 남는다. 그 위에서 `route_page()`가
    "○월 출발이 가장 저렴합니다"를 쓰므로 **살 수 없는 달을 추천하게 된다** —
    2026-09-08에 실제로 5개 노선이 "8월/7월 출발"을 권하고 있었다.

    **표본 임계로는 못 거른다.** 그날 ICN-NRT의 2026-08 버킷은 915건으로
    전체에서 가장 튼튼했다. 얇아서 틀린 게 아니라 **지나서** 틀린 것이라
    거르는 축이 다르다 — 임계가 아니라 창이다.

    `today_kst()`인 이유: 사용자의 '오늘'은 KST다. 새벽 3시 KST(전날 18시 UTC)에
    UTC 날짜로 거르면 한국 사용자에겐 이미 지난 달이 하루 더 남는다.

    `min_samples`·`limit`은 **임계**라서 계약상 프론트 몫이다(v1은 `None`으로 끈다).
    기본값이 현행 화면 동작인 이유: 이전이 끝날 때까지 `route_page()`가 이 함수를
    **같이 쓰기 때문이다.** 기본값이 바뀌면 라이브 화면이 움직이고 M2 기준선이 무효가 된다.
    """
    sql = """SELECT strftime('%Y-%m', depart_date) AS m, MIN(price), COUNT(*)
             FROM offers
             WHERE origin=? AND destination=? AND length(depart_date)=10
               AND depart_date>=?
             GROUP BY m HAVING COUNT(*)>=? ORDER BY m"""
    args = [origin, dest, timeutil.today_kst().isoformat(), min_samples]
    if limit is not None:
        sql, args = sql + " LIMIT ?", args + [limit]
    return conn.execute(sql, args).fetchall()


def weekday_min(conn, origin, dest, min_samples=1):
    """출발요일별 (**정수 wd**, 최저가, 표본수). 월요일부터 정렬해 돌려준다.

    🔴 **표시명이 아니라 정수를 낸다.** `'화'`로 바꾸는 건 표시 결정이고,
    그건 소비하는 쪽 몫이다(계약 §「배열 순서를 믿지 말고 `wd`를 읽어라」).
    월요일부터 정렬하는 것도 표시 관례라 순서에 의미를 두면 안 된다.

    **창을 걸지 않는다** — 요일은 순환하므로 지난 화요일의 가격도
    "화요일은 싼가"에 대한 유효한 증거다. `month_min`과 다른 이유가 여기 있다.

    `min_samples=1`은 필터가 없는 것과 같다(`GROUP BY`의 모든 묶음이 1건 이상).
    현행 화면 동작을 그대로 두려는 기본값이다.
    """
    rows = {wd: (p, n) for wd, p, n in conn.execute(
        """SELECT CAST(strftime('%w', depart_date) AS INTEGER) AS wd,
                  MIN(price), COUNT(*)
           FROM offers WHERE origin=? AND destination=? AND length(depart_date)=10
           GROUP BY wd HAVING COUNT(*)>=?""", (origin, dest, min_samples))}
    return [(wd, *rows[wd]) for wd in WEEK_ORDER if wd in rows]


def airline_min(conn, origin, dest, limit=8):
    """항공사별 (코드, 최저가, 표본수) — 최근 30일. 싼 순.

    30일은 **창**이라 유지한다. `limit`은 "상위 몇 개를 보여주나"라 **임계**다.
    """
    sql = """SELECT airline, MIN(price), COUNT(*) FROM offers
             WHERE origin=? AND destination=? AND fetched_date>=?
             GROUP BY airline ORDER BY MIN(price)"""
    args = [origin, dest,
            (timeutil.today_utc() - timedelta(days=WINDOW_DAYS)).isoformat()]
    if limit is not None:
        sql, args = sql + " LIMIT ?", args + [limit]
    return conn.execute(sql, args).fetchall()


def route_summary(conn, origin, dest):
    """(최저가, 중앙값, 표본수) — 최근 30일 전체."""
    since = (timeutil.today_utc() - timedelta(days=WINDOW_DAYS)).isoformat()
    prices = [p for (p,) in conn.execute(
        "SELECT price FROM offers WHERE origin=? AND destination=? AND fetched_date>=? ORDER BY price",
        (origin, dest, since))]
    if not prices:
        return None, None, 0
    return prices[0], prices[len(prices) // 2], len(prices)
