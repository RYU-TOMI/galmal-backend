# -*- coding: utf-8 -*-
"""발견 지도 데이터 계약 — broad_offers + dests 메타를 조인해 docs/data/deals.json 생성.

프론트(지도+피드)는 오직 이 JSON에만 의존한다. 스키마:
{
  "updated": "YYYY-MM-DD HH:MM",
  "origins": { "SEL": {"name":"서울","lat":..,"lon":..}, ... },
  "deals": [ {
     "o","d","ko","country","region","haul","tier","tags":[...],"lat","lon",
     "price","transfers","dep","ret","nights","median","discount","when",
     "low","obs_days","seen"
  }, ... ]
}
정책: 최근 3일 수집 + 미래 출발만, dests 사전(좌표) 있는 목적지만(데이터 게이팅),
      seen(가격 관측 시각)이 7일 넘은 딜 제외, (출발지, 도시) 단위 최저가 1건
      (인천+김포=서울 통합).
"""
import json
from datetime import date, timedelta
from pathlib import Path

import dests
import timeutil
from affiliates import compare_links
# `found_at`이 UTC라는 사실은 timeutil이 아는 유일한 곳이다 — 여기서 다시 구현하면
# 두 곳이 어긋난다. 실제로 fetch_breadth가 그렇게 어긋나 있었다(BB11).
from timeutil import parse_found_at as _seen_kst
DOCS = Path(__file__).resolve().parent.parent / "docs"
STALE_DAYS = 3
# seen(가격 관측 시각)이 이보다 오래된 딜은 내보내지 않는다 — 계약이 요구하는
# "영원히 안 죽는 유령 가격" 안전선이다(CONTRACT.md 2026-08-22).
#
# ⚠️ **지금은 구조적으로 발동하지 않는다.** 후보 행의 seen 나이 상한이
#    `MAX_AGE_HOURS`(96h=4일) + `STALE_DAYS`(3일) = **정확히 7일**이기 때문이다.
#    수집이 4일 넘은 가격을 안 받고, 받은 뒤 창에 3일까지만 머문다.
#    실측(2026-09-01): 창 안 493건 중 최대 6.96일, 컷 대상 0건.
#    → 그래도 남겨 둔다. 수집 컷(`MAX_AGE_HOURS`)이나 창(`STALE_DAYS`)이 넓어지면
#      그때부터 실제로 막는다. 없애면 그 변경이 조용히 유령 가격을 통과시킨다.
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

# `median`·`low`·`obs_days`가 보는 이력의 **가장 오래된 경계**. 창이 없으면 이력이
# 길어질수록 중앙값이 옛 가격에 끌려가 할인율이 부풀려진다(BB4).
#
# ⚠️ 실제로 보는 폭은 30일이 아니라 **27일**이다. 이 값은 `today - 30`이라는 하한이고,
#    위쪽은 `cutoff`(= `today - STALE_DAYS`)에서 잘리기 때문이다. 즉 `obs_days`는
#    27을 넘을 수 없다. 이름과 동작이 어긋나면 아무도 실제 창을 모른다(BB10에서 겪었다).
HISTORY_FLOOR_DAYS = 30
HISTORY_SPAN_DAYS = HISTORY_FLOOR_DAYS - STALE_DAYS      # = 27, 실제로 보는 폭

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


def _route_code(origin_airport, dest, available):
    """그 딜에 해당하는 노선 페이지 코드. 없으면 None.

    **프론트가 판정할 수 없어서 여기서 넣는다.** 허브 `o`가 가상(`SEL`)이라
    `deals.json`만 봐서는 인천인지 김포인지 알 수 없고, 프론트가 `ICN`으로
    추측하면 부산 딜을 인천 노선 페이지로 보내는 것과 같은 오류가 된다.

    ⚠️ `config.ROUTES` 목록이 아니라 **이번 빌드가 실제로 만든 페이지**(`available`)로
    판정한다. `route_page()`는 수집 이력이 없으면 파일을 만들지 않으므로, 노선을
    새로 추가한 날에는 목록에 있어도 페이지가 없다. 목록만 보면 프론트가 404로 간다.
    """
    code = f"{origin_airport}-{dest}"
    return code if code in available else None


def _previous_deal_count():
    """커밋돼 있는 `deals.json`의 딜 수. 없거나 못 읽으면 None."""
    path = DOCS / "data" / "deals.json"
    try:
        return len(json.loads(path.read_text(encoding="utf-8"))["deals"])
    except (OSError, ValueError, KeyError, TypeError):
        return None


def _prior_history(conn, cutoff, floor):
    """`(허브, 도시)` → `(평소 시세, 이전 기간 최저가, 관측 일수)`.

    **"이전 기간"은 이번 수집 창(`cutoff` 이후)을 뺀 그 앞이다.** 오늘 값을 포함하면
    "역대 최저냐"가 동어반복이 된다 — `deals.json`의 `price`가 이미 최근 3~4일 중
    최저가라서, 그걸 넣고 최저인지 물으면 41%가 "최저"로 나온다(2026-09-01 실측).
    이력이 없으면 호출부가 `(None, 0)`으로 받는다.

    알갱이가 `(허브, 한글도시명)`인 이유: 딜의 중복 제거 키와 같아야 한다. 딜 하나가
    도시 하나를 가리키므로 이력도 도시 단위로 봐야 "17일 중 최저"가 그 카드의 말이 된다.

    **셋 다 같은 것을 재고 같은 기간을 본다** — "그 도시 그날 최저가"의 이전 기간 분포.
    `median`은 그 분포의 가운데, `low`는 바닥, `obs_days`는 표본 수다. 그래야 한 카드
    안에서 말이 맞는다. 예전엔 `median`만 `(실공항, IATA)` 단위였고(BB4), `price`가
    도시 단위 최저가라 **사과와 오렌지를 비교**하고 있었다.

    `floor`(30일) 이전은 보지 않고, `cutoff`(이번 수집 창) 이후도 보지 않는다.
    창을 안 두면 중앙값이 옛 가격에 끌려가고, 오늘을 넣으면 비교 대상이 자기 자신이 된다.
    이력이 없으면 키 자체가 없어 호출부가 `(None, None, 0)`을 받는다 — BB12대로
    **모르는 값을 지어내지 않는다.**
    """
    daily = {}                       # (허브,도시) -> {날짜: 그날 그 도시 최저가}
    for o, d, fd, price in conn.execute(
            """SELECT origin, destination, fetched_date, price FROM broad_offers
               WHERE fetched_date >= ? AND fetched_date < ? AND price IS NOT NULL""",
            (floor, cutoff)):
        hub = ORIGIN_NORM.get(o)
        meta = dests.DEST.get(d)
        if not hub or not meta:
            continue
        by_day = daily.setdefault((hub, meta[0]), {})
        if fd not in by_day or price < by_day[fd]:
            by_day[fd] = price
    return {k: (_median(list(v.values())), min(v.values()), len(v))
            for k, v in daily.items()}


def _when_label(dep, today):
    """출발일을 상대 날짜 라벨로. 어휘와 순서는 `CONTRACT.md` §when이 못 박는다.

    **달력 단위로 잰다.** 예전엔 "N일 이내"라는 상대 거리로 재면서 라벨은 달력을
    말해서, 다음 주 것이 이번 주로 표기됐다(BB21).

        9/12(토) 접속 · 옛 규칙
          9/18(금) +6 → "이번 주말"   ← 다음 주말인데
          9/14(월) +2 → "이번 주"     ← 다음 주인데

    `이번 주말`은 금·토·일에 접속하면 3일이 통째로, `이번 주`는 월요일 접속에도
    어긋났다. 원인이 하나라 함께 고쳤다.

    `다음 주말`을 따로 두는 이유: 달력으로만 고치면 다음 주말이 `이번 달`로 떨어져
    임박 신호를 잃는다. 여행에서 주말은 특별한 단위다. 다음 주 **평일**은 그만큼
    중요하지 않으므로 `이번 달`로 둔다(기획 판단).

    주는 **월요일 시작**이다(한국 관례). 1·2가 4·5보다 먼저라, 9/30(수)에 10/3(토)이면
    `다음 달`이 아니라 `이번 주말`이다 — 달을 넘어도 이번 주면 이번 주다.
    """
    monday = today - timedelta(days=today.weekday())     # 이번 주 월요일
    this_week = {monday + timedelta(days=i) for i in range(7)}
    next_week = {monday + timedelta(days=7 + i) for i in range(7)}

    if dep in this_week and dep.weekday() >= 4:          # 1. 이번 주 금·토·일
        return "이번 주말"
    if dep in next_week and dep.weekday() >= 4:          # 2. 다음 주 금·토·일
        return "다음 주말"
    if dep in this_week:                                 # 3. 이번 주 나머지
        return "이번 주"
    if (dep.year, dep.month) == (today.year, today.month):
        return "이번 달"
    nxt = today.month % 12 + 1
    nxt_year = today.year + (1 if today.month == 12 else 0)
    if (dep.year, dep.month) == (nxt_year, nxt):
        return "다음 달"
    years = dep.year - today.year
    if years == 1:
        return f"내년 {dep.month}월"
    if years >= 2:
        return f"{dep.year}년 {dep.month}월"
    return f"{dep.month}월"


def build_deals_json(conn, routes=None):
    """`routes` — 이번 빌드가 실제로 만든 노선 페이지 코드 집합(`{"ICN-FUK", ...}`).
    `build_site`가 넘긴다. 생략하면 `route`는 전부 `None`이 된다."""
    routes = routes or set()
    now = timeutil.now_kst()
    today = now.date()          # 제품용 '오늘'은 KST — 사용자 기준이다(BB17)
    seen_floor = now - timedelta(days=SEEN_MAX_DAYS)
    cutoff = (today - timedelta(days=STALE_DAYS)).isoformat()
    rows = conn.execute(
        """SELECT origin, destination, price, transfers, depart_date, return_date,
                  found_at
           FROM broad_offers
           WHERE fetched_date >= ? AND depart_date >= ? AND price IS NOT NULL""",
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

    prior = _prior_history(conn, cutoff,
                           (today - timedelta(days=HISTORY_FLOOR_DAYS)).isoformat())

    deals = []
    for dd in best.values():
        lat, lon = dests.dest_coord(dd["d"])
        med, low, obs_days = prior.get((dd["o"], dd["ko"]), (None, None, 0))
        # 이력이 없으면 할인율도 0이다. 모르는 시세를 지어내 "몇 % 싸다"고 말하지 않는다.
        if med is None or med <= dd["price"]:
            disc = 0
        else:
            disc = max(0, min(round((med - dd["price"]) / med * 100), 70))
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
            # 이전 관측 기간의 최저가와 관측 일수. 프론트가 `price < low`로 신기록을
            # 판정하고 `(1 - price/low)`로 낙폭까지 계산한다. 임계값은 프론트 파생이라
            # 이력이 쌓여 비율이 변해도 계약을 안 건드리고 조정할 수 있다.
            "low": low, "obs_days": obs_days,
            # 절대 시각만 준다 — "3시간 전" 같은 문구를 구우면 정적 페이지라
            # 다음 날 방문자에게 거짓말이 된다. 나이 계산은 프론트 몫.
            "seen": dd["seen"].isoformat() if dd["seen"] else None,
            # 노선 페이지 코드. 실제 공항(_oi)으로 판정한다 — 허브(o)로는 안 된다.
            "route": _route_code(dd["_oi"], dd["d"], routes),
            # 예약처 비교 링크:
            #   출발 — 실제 공항코드(_oi: ICN/GMP/PUS…). SEL은 공항이 아니고,
            #          우리가 그 공항을 지정해 물었으므로 아는 값이다.
            #   목적 — 도시 코드로 넓힌다(NRT→TYO). 광역 수집이 도시 단위라
            #          어느 공항인지 모르는데 하나로 좁히면 우리가 보여준 가격이
            #          검색 결과에 없을 수 있다. 예약처 4곳 모두 도시 코드를 받는다.
            "links": compare_links(dd["_oi"], dests.link_code(dd["d"]),
                                   dd["dep"], dd["ret"]),
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
    n = build_deals_json(conn)          # 단독 실행 시 route는 전부 None
    conn.close()
    print("deals.json 유지(하한선 미달)" if n < 0 else f"deals.json 생성: {n}건")
