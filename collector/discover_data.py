# -*- coding: utf-8 -*-
"""발견 지도 데이터 계약 — broad_offers + dests 메타를 조인해 docs/data/deals.json 생성.

프론트(지도+피드)는 오직 이 JSON에만 의존한다. 스키마:
{
  "updated": "YYYY-MM-DD HH:MM",
  "origins": { "SEL": {"name":"서울","lat":..,"lon":..}, ... },
  "deals": [ {
     "o","d","ko","country","region","haul","tier","tags":[...],"lat","lon",
     "price","transfers","dep","ret","nights","median","discount","when"
  }, ... ]
}
정책: 최근 3일 수집 + 미래 출발만, dests 사전(좌표) 있는 목적지만(데이터 게이팅),
      (출발지, 도시) 단위 최저가 1건(인천+김포=서울 통합).
"""
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import dests
from affiliates import compare_links

KST = timezone(timedelta(hours=9))
DOCS = Path(__file__).resolve().parent.parent / "docs"
STALE_DAYS = 3

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
    cutoff = (today - timedelta(days=STALE_DAYS)).isoformat()
    rows = conn.execute(
        """SELECT origin, destination, price, transfers, depart_date, return_date
           FROM broad_offers
           WHERE fetched_date >= ? AND depart_date >= ?""",
        (cutoff, today.isoformat())).fetchall()

    # (정규화 출발지, 도시) 단위로 최저가 딜만 남긴다
    best = {}
    for o, d, price, tr, dep, ret in rows:
        norm = ORIGIN_NORM.get(o)
        if not norm or not (dests.is_destination(d) and dests.dest_coord(d)):
            continue
        ko, country, region, haul, tags = dests.DEST[d]
        key = (norm, ko)
        cur = best.get(key)
        if cur is None or price < cur["price"]:
            best[key] = {"o": norm, "d": d, "ko": ko, "country": country,
                         "region": region, "haul": haul, "tags": tags,
                         "tier": dests.tier(d), "price": price, "transfers": tr,
                         "dep": dep, "ret": ret, "_oi": o}

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
            # 예약처 비교 링크는 실제 공항코드(_oi: ICN/GMP/PUS…)로 — SEL은 공항이 아님
            "links": compare_links(dd["_oi"], dd["d"], dd["dep"], dd["ret"]),
        })

    deals.sort(key=lambda x: x["price"])
    origins = {k: {"name": v[0], "lat": v[1], "lon": v[2]}
               for k, v in ORIGIN_HUBS.items() if any(dl["o"] == k for dl in deals)}
    out = {"updated": datetime.now(KST).strftime("%Y-%m-%d %H:%M"),
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
