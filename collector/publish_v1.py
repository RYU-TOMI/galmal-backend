# -*- coding: utf-8 -*-
"""v1 API 발행 — `docs/v1/` (`CONTRACT.md` §v1, `SPLIT.md` M1 T2).

**백엔드가 HTTP로 응답하는 것처럼 행동한다.** 오늘은 GitHub Pages가 정적 JSON을
서빙하고, 자체 서버가 생기면 DNS만 옮긴다 — 프론트는 한 글자도 안 바뀐다.
그래서 노선을 **파일 하나로 묶지 않고 코드마다 쪼갠다.** 그대로 라우트가 된다.

    GET /v1/meta.json           생성 시각·건수·수집 상태·구독 규약
    GET /v1/deals.json          발견 홈이 쓰는 전부
    GET /v1/routes/index.json   노선 목록
    GET /v1/routes/{code}.json  노선 1개 통계

**이 모듈은 이전이 끝나도 남는다.** `build_site.py`의 HTML 부분이 프론트로 가고 나면
여기가 백엔드의 출구가 된다. 그래서 화면을 몰라야 하고, 실제로 모른다 —
`fmt_month`도 `SQL_WEEKDAY`도 import하지 않는다.

## 이 파일이 지키는 두 가지

**① 완성된 문장을 만들지 않는다** (`CONTRACT.md` P7).
`"2026-09"`를 보내지 `"9월"`을 보내지 않는다. `wd=1`을 보내지 `"월"`을 보내지 않는다.
표시명이 필요하면 그건 `COPY.md`의 일이고 프론트가 붙인다.

**② 얇다고 버리지 않는다** — 창은 백엔드, 임계는 프론트.
`month_min`의 `min_samples`·`limit`을 **끄고** 부른다. 3건짜리 달도 `n`과 함께 내보내고,
자를지는 프론트가 정한다. 지금 화면이 3건 미만을 버리는 건 `route_page()`가
기본값으로 부르기 때문이고, **그 기본값은 이전이 끝날 때까지만 산다.**
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config
import subscriptions
import theme
import timeutil
# 🔴 `build_site`를 import하지 않는다 — 옛 HTML 쪽이고 M3에서 사라진다.
# 통계는 `route_stats`, 경로는 `discover_data`(둘 다 이전 후에도 남는 모듈)에서 온다.
from discover_data import DOCS
from route_stats import (WINDOW_DAYS, airline_min, daily_min, month_min,
                         route_summary, weekday_min)
from labels import airline_name, city, region_of

SCHEMA = "v1"
V1 = DOCS / "v1"


def _write(rel_path, payload):
    """`docs/v1/<rel_path>`에 쓴다. 압축 없음, UTF-8 (`CONTRACT.md` §공통 규칙)."""
    path = V1 / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
                    encoding="utf-8")
    return path


def _envelope(generated=None):
    """모든 응답의 최상위 두 키.

    `generated`는 **ISO 8601 + 오프셋 필수**다. 화면이 신선도를 표시하고 있어
    (`발견가 · N일 전 가격`) 날짜 경계에서 오프셋이 없으면 하루가 조용히 어긋난다.
    현행 `updated`의 `"2026-08-06 00:15"`는 **완성된 문장**이라 v1에선 쓰지 않는다.
    """
    return {"schema": SCHEMA,
            "generated": (generated or timeutil.now_kst()).isoformat(timespec="seconds")}


# ---------------------------------------------------------------- 1) meta.json

def meta_payload(counts, preserved, generated=None):
    """구독 규약이 여기 실리는 이유는 `CONTRACT.md` §subscribe에 있다 — 요약하면
    **표시가 아니라 전선(wire) 규약**이라서다. 프론트가 본문 형식을 지어내면
    구독 실패가 아니라 **전 노선 구독**이 된다(`subscriptions.py:61` `route or "ALL"`).

    🔴 **값은 파서 상수에서 파생시킨다.** `theme.py`는 M3에서 프론트로 가므로
    거기서 문자열을 가져오면 이전하는 날 출처가 갈린다. 제목 두 개는
    `subscriptions`가 **실제로 읽는 바로 그 상수**다.
    """
    return {
        **_envelope(generated),
        "window_days": WINDOW_DAYS,
        "counts": counts,
        "preserved": preserved,
        "subscribe": {
            "address": theme.SUBSCRIBE_ADDR,
            "subject_subscribe": subscriptions.SUBSCRIBE,
            "subject_unsubscribe": subscriptions.UNSUBSCRIBE,
            # ROUTE_RE 가 받는 형태. 정규식 자체를 노출할 필요는 없다.
            "route_token": "{code}",
        },
    }


# ---------------------------------------------------------------- 2) deals.json

def deals_payload():
    """현행 `docs/data/deals.json`을 **다시 봉투에 넣는다.**

    왜 다시 계산하지 않나: 같은 사실을 두 번 계산하면 갈라진다. 이 저장소가
    반복해 만난 그 유형이고(`timeutil`·`labels.city`·`theme.BASE_URL`),
    지금은 두 산출물이 **같은 딜 목록**을 내야 하는 상태다.

    **하한선 미달(BB1)일 때도 저절로 맞는다** — 그날 `build_deals_json()`은 파일을
    안 쓰고 어제 것을 남긴다. 여기서 그 파일을 읽으므로 v1도 어제 것을 그대로 낸다.
    `generated`가 어제 시각인 것도 옳다. **어제 데이터에 오늘 도장을 찍는 게 더 나쁘다.**
    그 상태는 `meta.preserved`가 따로 말한다.

    반환: `(payload, 딜 수, 허브 수)`. 파일이 없으면 `(None, 0, 0)`.
    """
    src = DOCS / "data" / "deals.json"
    if not src.exists():
        return None, 0, 0
    cur = json.loads(src.read_text(encoding="utf-8"))
    # `updated`는 KST 표시 문자열이다. 오프셋을 붙여 계약 형식으로 되돌린다.
    stamped = timeutil.parse_kst_stamp(cur.get("updated"))
    payload = {**_envelope(stamped),
               "origins": cur.get("origins", {}),
               "deals": cur.get("deals", [])}
    return payload, len(payload["deals"]), len(payload["origins"])


# ------------------------------------------------------- 3)·4) routes/*.json

def route_payload(conn, origin, dest, generated=None):
    """노선 1개. 표본이 0이면 `None` — 그런 노선은 **응답 자체가 없다.**

    `min_samples`·`limit`을 끄고 부르는 게 이 함수의 요점이다.
    현행 화면이 3건 미만인 달을 버리는 건 `route_page()`의 기본값이지 **사실이 아니다.**
    """
    cheapest, median, n = route_summary(conn, origin, dest)
    if not n:
        return None
    return {
        **_envelope(generated),
        "code": f"{origin}-{dest}",
        "o": origin, "d": dest,
        "o_name": city(origin), "d_name": city(dest),
        "region": region_of(dest),
        "window_days": WINDOW_DAYS,
        "summary": {"cheapest": cheapest, "median": median, "n": n},
        # trend 에는 n 이 없다 — 하루 = 한 점이라 항상 1에 수렴한다(계약 §필드 주의)
        "trend": [{"date": d, "price": p}
                  for d, p in daily_min(conn, origin, dest, WINDOW_DAYS)],
        "months": [{"m": m, "price": p, "n": cnt}
                   for m, p, cnt in month_min(conn, origin, dest,
                                              min_samples=1, limit=None)],
        "weekdays": [{"wd": wd, "price": p, "n": cnt}
                     for wd, p, cnt in weekday_min(conn, origin, dest)],
        # 항공사 표시명은 **참조 데이터**다 — `deal.ko`와 같은 성격이라
        # 백엔드가 낸다. 문장이 아니라 사실이므로 P7에 걸리지 않는다.
        "airlines": [{"code": a, "name": airline_name(a), "min": p, "n": cnt}
                     for a, p, cnt in airline_min(conn, origin, dest, limit=None)],
    }


def publish(conn):
    """v1 4종을 전부 쓴다. 반환: 발행한 노선 수."""
    generated = timeutil.now_kst()
    routes = []
    for origin, dest in config.ROUTES:
        payload = route_payload(conn, origin, dest, generated)
        if not payload:
            continue
        _write(f"routes/{payload['code']}.json", payload)
        routes.append({"code": payload["code"], "o": origin, "d": dest,
                       "o_name": payload["o_name"], "d_name": payload["d_name"],
                       "region": payload["region"],
                       "cheapest": payload["summary"]["cheapest"]})

    # 정렬은 config.ROUTES 순서 그대로. 프론트가 필요한 순서로 다시 정렬한다.
    _write("routes/index.json", {**_envelope(generated), "routes": routes})

    deals, n_deals, n_origins = deals_payload()
    if deals is not None:
        _write("deals.json", deals)

    # `preserved`의 정본은 딜 산출물의 시각이다 — 오늘 것이 아니면 갱신을 건너뛴 것이다.
    preserved = bool(deals) and deals["generated"][:10] != generated.date().isoformat()
    _write("meta.json", meta_payload(
        {"deals": n_deals, "routes": len(routes), "origins": n_origins},
        preserved, generated))
    return len(routes)


if __name__ == "__main__":
    import db
    conn = db.connect()
    print(f"v1 발행: 노선 {publish(conn)}개")
    conn.close()
