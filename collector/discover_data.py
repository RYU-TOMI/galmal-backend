# -*- coding: utf-8 -*-
"""발견 지도 데이터 계약 — broad_offers + dests 메타를 조인해 docs/data/deals.json 생성.

프론트(지도+피드)는 오직 이 JSON에만 의존한다. 스키마:
{
  "updated": "YYYY-MM-DD HH:MM",
  "origins": { "SEL": {"name":"서울","lat":..,"lon":..}, ... },
  "deals": [ {
     "o","d","ko","country","region","haul","tier","tags":[...],"lat","lon",
     "price","transfers","dep","ret","nights","median","discount","when","seen"
  }, ... ]
}
정책: 최근 3일 수집 + 미래 출발만, dests 사전(좌표) 있는 목적지만(데이터 게이팅),
      seen(가격 관측 시각)이 7일 넘은 딜 제외, (출발지, 도시) 단위 최저가 1건
      (인천+김포=서울 통합).
"""
import json
from datetime import date, datetime, timedelta
from pathlib import Path

import dests
import timeutil
from affiliates import compare_links
# `found_at`이 UTC라는 사실은 timeutil이 아는 유일한 곳이다 — 여기서 다시 구현하면
# 두 곳이 어긋난다. 실제로 fetch_breadth가 그렇게 어긋나 있었다(BB11).
from timeutil import KST
from timeutil import parse_found_at as _seen_kst
DOCS = Path(__file__).resolve().parent.parent / "docs"
STALE_DAYS = 3
# seen(가격 관측 시각)이 이보다 오래된 딜은 내보내지 않는다 — 영원히 안 죽는
# 유령 가격만 막는 안전선이다. 3일로 조이면 딜 26%와 소도시 롱테일이 먼저
# 잘리므로 하지 않는다(CONTRACT.md / DECISIONS.md 2026-08-22).
SEEN_MAX_DAYS = 7

# 산출물 보호(BB1) — 수집이 무너진 날 좋은 파일을 나쁜 파일로 덮지 않는다.
#
# 값 근거(2026-09-01, 30일 재현 실측): 딜 수는 최소 99 · 중앙 110 · 최대 126,
# 전날 대비 하루 변동은 **최대 -12.5%**였다. 그러니 절대 30건 미만이나 전날의
# 절반 이하는 정상 변동이 아니라 사고다.
#
# ⚠️ 잠금 방지: 이전 산출물 자체가 하한선 미만이면 이 검사를 걸지 않는다.
#    안 그러면 한 번 망가진 파일이 영원히 보존돼 정상 데이터가 못 들어온다.
MIN_DEALS = 30
MIN_RATIO = 0.5

# 정규화 출발지 → (표시명, lat, lon). 인천+김포 = 서울 통합.
ORIGIN_HUBS = {
    "SEL": ("서울", 37.55, 126.99),
    "PUS": ("부산", 35.18, 128.94),
    "TAE": ("대구", 35.90, 128.66),
    "CJU": ("제주", 33.51, 126.49),
}
ORIGIN_NORM = {"ICN": "SEL", "GMP": "SEL", "PUS": "PUS", "TAE": "TAE", "CJU": "CJU"}


def _median(vals):
    s = sorted(vals)
    n = len(s)
    if not n:
        return None
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) // 2


def _previous_deal_count():
    """커밋돼 있는 `deals.json`의 딜 수. 없거나 못 읽으면 None."""
    path = DOCS / "data" / "deals.json"
    try:
        return len(json.loads(path.read_text(encoding="utf-8"))["deals"])
    except (OSError, ValueError, KeyError, TypeError):
        return None


def _when_label(dep, today):
    delta = (dep - today).days
    if 0 <= delta <= 9 and dep.weekday() >= 4:   # 금·토·일 출발이 임박
        return "이번 주말"
    if delta <= 7:
        return "이번 주"
    nxt = today.month % 12 + 1
    nxt_year = today.year + (1 if today.month == 12 else 0)
    if dep.month == nxt and dep.year == nxt_year:
        return "다음 달"
    return f"{dep.month}월"


def build_deals_json(conn):
    now = timeutil.now_kst()
    today = now.date()          # 제품용 '오늘'은 KST — 사용자 기준이다(BB17)
    seen_floor = now - timedelta(days=SEEN_MAX_DAYS)
    cutoff = (today - timedelta(days=STALE_DAYS)).isoformat()
    rows = conn.execute(
        """SELECT origin, destination, price, transfers, depart_date, return_date,
                  found_at
           FROM broad_offers
           WHERE fetched_date >= ? AND depart_date >= ?""",
        (cutoff, today.isoformat())).fetchall()

    # (정규화 출발지, 도시) 단위로 최저가 딜만 남긴다.
    # 유령 가격 컷은 **중복 제거 앞에** 둔다 — 뒤에 두면 오래된 싼 값이 대표로
    # 뽑힌 뒤 잘려나가면서, 같은 도시의 멀쩡한 딜까지 함께 사라진다.
    best = {}
    for o, d, price, tr, dep, ret, found in rows:
        norm = ORIGIN_NORM.get(o)
        if not norm or not (dests.is_destination(d) and dests.dest_coord(d)):
            continue
        seen = _seen_kst(found)
        if seen is not None and seen < seen_floor:
            continue
        ko, country, region, haul, tags = dests.DEST[d]
        key = (norm, ko)
        cur = best.get(key)
        if cur is None or price < cur["price"]:
            best[key] = {"o": norm, "d": d, "ko": ko, "country": country,
                         "region": region, "haul": haul, "tags": tags,
                         "tier": dests.tier(d), "price": price, "transfers": tr,
                         "dep": dep, "ret": ret, "seen": seen, "_oi": o}

    deals = []
    for dd in best.values():
        lat, lon = dests.dest_coord(dd["d"])
        hist = [p for (p,) in conn.execute(
            "SELECT price FROM broad_offers WHERE origin=? AND destination=?",
            (dd["_oi"], dd["d"]))]
        med = _median(hist) or dd["price"]
        disc = round((med - dd["price"]) / med * 100) if med > dd["price"] else 0
        disc = max(0, min(disc, 70))
        dep = date.fromisoformat(dd["dep"])
        ret = date.fromisoformat(dd["ret"]) if dd["ret"] else None
        n = (ret - dep).days if ret else 0
        deals.append({
            "o": dd["o"], "d": dd["d"], "ko": dd["ko"], "country": dd["country"],
            "region": dd["region"], "haul": dd["haul"], "tier": dd["tier"],
            "tags": dd["tags"], "lat": lat, "lon": lon,
            "price": dd["price"], "transfers": dd["transfers"],
            "dep": dd["dep"], "ret": dd["ret"],
            "nights": (f"{n}박{n + 1}일" if n else ""),
            "median": med, "discount": disc, "when": _when_label(dep, today),
            # 절대 시각만 준다 — "3시간 전" 같은 문구를 구우면 정적 페이지라
            # 다음 날 방문자에게 거짓말이 된다. 나이 계산은 프론트 몫.
            "seen": dd["seen"].isoformat() if dd["seen"] else None,
            # 예약처 비교 링크는 실제 공항코드(_oi: ICN/GMP/PUS…)로 — SEL은 공항이 아님
            "links": compare_links(dd["_oi"], dd["d"], dd["dep"], dd["ret"]),
        })

    deals.sort(key=lambda x: x["price"])

    # 수집이 무너진 날 빈 산출물로 덮어쓰지 않는다(BB1 / 기획 F1).
    # 파일을 아예 쓰지 않으면 `build_index()`가 기존 파일을 읽어 그대로 인라인하므로
    # index.html도 같은 내용으로 재생성되고, git이 변경 없음으로 보아 커밋조차 안 생긴다.
    # `updated`도 예전 시각 그대로 남는데 그게 옳다 — 어제 데이터에 오늘 도장을 찍는 것이
    # 더 나쁘다(기획 합의 2026-08-22). seen 배지가 저절로 늙어 상태를 대신 말해 준다.
    prev = _previous_deal_count()
    if prev is not None and prev >= MIN_DEALS:
        if len(deals) < MIN_DEALS or len(deals) < prev * MIN_RATIO:
            print(f"⚠️  deals.json을 갱신하지 않는다: {len(deals)}건 "
                  f"(이전 {prev}건 · 하한 {MIN_DEALS}건 또는 이전의 {MIN_RATIO:.0%})")
            print("    수집 실패·목적지 코드 변경·신선도 컷을 의심할 것. "
                  "이전 산출물을 그대로 둔다.")
            return -1

    origins = {k: {"name": v[0], "lat": v[1], "lon": v[2]}
               for k, v in ORIGIN_HUBS.items() if any(dl["o"] == k for dl in deals)}
    out = {"updated": now.strftime("%Y-%m-%d %H:%M"),
           "origins": origins, "deals": deals}
    (DOCS / "data").mkdir(parents=True, exist_ok=True)
    (DOCS / "data" / "deals.json").write_text(
        json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return len(deals)


if __name__ == "__main__":
    import db
    conn = db.connect()
    n = build_deals_json(conn)
    conn.close()
    print("deals.json 유지(하한선 미달)" if n < 0 else f"deals.json 생성: {n}건")
