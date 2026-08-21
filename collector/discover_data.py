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
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import dests
from affiliates import compare_links

KST = timezone(timedelta(hours=9))
DOCS = Path(__file__).resolve().parent.parent / "docs"
STALE_DAYS = 3
# seen(가격 관측 시각)이 이보다 오래된 딜은 내보내지 않는다 — 영원히 안 죽는
# 유령 가격만 막는 안전선이다. 3일로 조이면 딜 26%와 소도시 롱테일이 먼저
# 잘리므로 하지 않는다(CONTRACT.md / DECISIONS.md 2026-08-22).
SEEN_MAX_DAYS = 7

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


def _seen_kst(raw):
    """API의 `found_at`을 KST aware datetime으로. 변환 불가면 None.

    원본은 **오프셋 없는 UTC 문자열**이다. 그대로 KST처럼 다루면 모든 가격이
    9시간씩 늙어 보인다. 근거(2026-08-22 실측): UTC로 해석해야 매일 가장 신선한
    가격의 나이가 0h 부근으로 떨어진다 — 캐시가 방금 관측한 값을 돌려주는
    자연스러운 그림이다. KST로 보면 최신값조차 8.8h 된 것이 되고, 최대 나이가
    수집 필터 자신의 컷(96h)을 넘어 저장 자체가 불가능해진다.

    이미 오프셋이 붙어 오는 경우(향후 API 변경)도 그대로 존중한다.
    """
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(raw)
    except (TypeError, ValueError):
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(KST)


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
    today = date.today()
    now = datetime.now(KST)
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
    print(f"deals.json 생성: {n}건")
