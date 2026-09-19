# -*- coding: utf-8 -*-
"""v1 API 발행 — `docs/v1/` (`CONTRACT.md` §v1). **백엔드의 유일한 출구다.**

M3 T3(2026-09-15)에 `build_site.py`가 사라지면서 화면 생성이 프론트(`site/`)로 넘어갔다.
백엔드는 이제 **HTML을 한 글자도 만들지 않는다.** 크론이 부르는 것도 이 파일 하나다.

**백엔드가 HTTP로 응답하는 것처럼 행동한다.** 오늘은 GitHub Pages가 정적 JSON을
서빙하고, 자체 서버가 생기면 DNS만 옮긴다 — 프론트는 한 글자도 안 바뀐다.
그래서 노선을 **파일 하나로 묶지 않고 코드마다 쪼갠다.** 그대로 라우트가 된다.

    GET /v1/meta.json           생성 시각·건수·수집 상태·구독 규약
    GET /v1/deals.json          발견 홈이 쓰는 전부
    GET /v1/routes/index.json   노선 목록
    GET /v1/routes/{code}.json  노선 1개 통계
    GET /v1/vocab.json          참조 데이터 — 통제 어휘 + 지역 표시명 (BE11)

**화면을 몰라야 하고, 실제로 모른다** — 월·요일 표시 포매터는 백엔드에 아예 없다(BE13 T3에서 지웠다).
P7(백엔드는 사실을, 프론트는 말을)은 `tests/test_publish.py`가 발행물의 문자열을 훑어 지킨다.

## 이 파일이 지키는 두 가지

**① 완성된 문장을 만들지 않는다** (`CONTRACT.md` P7).
`"2026-09"`를 보내지 `"9월"`을 보내지 않는다. `wd=1`을 보내지 `"월"`을 보내지 않는다.
표시명이 필요하면 그건 `COPY.md`의 일이고 프론트가 붙인다.

**② 얇다고 버리지 않는다** — 창은 백엔드, 임계는 프론트.
`month_min`의 `min_samples`·`limit`을 **끄고** 부른다. 3건짜리 달도 `n`과 함께 내보내고,
자를지는 프론트가 정한다. `route_stats`의 기본값(3건·10개)은 옛 화면의 규칙이고,
지금은 테스트가 「발행값에 그 임계를 걸면 옛 숫자가 나오는가」를 대조하는 기준으로만 쓴다.
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import affiliates
import config
import discover_data
import subscriptions
import timeutil
# 통계는 `route_stats`, 경로는 `discover_data`에서 온다.
from discover_data import DOCS
from route_stats import (WINDOW_DAYS, airline_min, daily_min, month_min,
                         route_summary, weekday_min)
from dests import REGION_NAME
from labels import airline_name, city, region_of

SCHEMA = "v1"
V1 = DOCS / "v1"
VOCAB_SRC = Path(__file__).resolve().parent.parent / "contract" / "v1" / "vocab.json"


def _write(rel_path, payload):
    """`docs/v1/<rel_path>`에 쓴다. 압축 없음, UTF-8 (`CONTRACT.md` §공통 규칙)."""
    path = V1 / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
                    encoding="utf-8")
    return path


def _envelope(generated):
    """모든 응답의 최상위 두 키.

    `generated`는 **ISO 8601 + 오프셋 필수**다. 화면이 신선도를 표시하고 있어
    (`발견가 · N일 전 가격`) 날짜 경계에서 오프셋이 없으면 하루가 조용히 어긋난다.
    현행 `updated`의 `"2026-08-06 00:15"`는 **완성된 문장**이라 v1에선 쓰지 않는다.

    🔴 **기본값이 없다** (BE9 T2, BB35). 한 번의 발행이 낸 응답은 모두 같은
    `generated`를 가져야 한다(CONTRACT §공통 규칙 — 프론트가 섞인 스냅숏을 이걸로 잡는다).
    예전엔 `generated or now_kst()`였다 — 새 payload가 넘기기를 빼먹으면 그 파일만
    초 단위로 갈리고 **프론트 배포가 매일 실패**한다. 빼먹는 순간 `TypeError`로 터지게 둔다.
    """
    if generated.tzinfo is None:
        raise ValueError(f"generated 에 오프셋이 없다: {generated!r}")
    return {"schema": SCHEMA,
            "generated": generated.isoformat(timespec="seconds")}


# ---------------------------------------------------------------- 1) meta.json

def meta_payload(counts, preserved, generated):
    """구독 규약이 여기 실리는 이유는 `CONTRACT.md` §subscribe에 있다 — 요약하면
    **표시가 아니라 전선(wire) 규약**이라서다. 프론트가 본문 형식을 지어내면
    구독 실패가 아니라 **전 노선 구독**이 된다(`subscriptions.py:61` `route or "ALL"`).

    🔴 **넷 다 파서 상수에서 파생시킨다.** 주소도 T5에서 `subscriptions`로 옮겼다 —
    `theme.py`가 프론트로 가는 날 출처가 갈리기 때문이다. 이제 `meta.subscribe`의
    네 값이 **전부 파서 한 모듈**에서 나온다.
    """
    return {
        **_envelope(generated),
        "window_days": WINDOW_DAYS,
        "counts": counts,
        "preserved": preserved,
        "subscribe": {
            "address": subscriptions.SUBSCRIBE_ADDR,
            "subject_subscribe": subscriptions.SUBSCRIBE,
            "subject_unsubscribe": subscriptions.UNSUBSCRIBE,
            # ROUTE_RE 가 받는 형태. 정규식 자체를 노출할 필요는 없다.
            "route_token": "{code}",
        },
    }


# ---------------------------------------------------------------- 2) deals.json

def deals_payload(conn, codes, generated):
    """딜 응답을 만든다. **하한선 미달이면 `None`** (BB1).

    T3 전에는 `docs/data/deals.json`을 읽어 다시 봉투에 넣었다. 그 파일이 사라져
    이제 `build_deals_json()`을 직접 부른다 — 중간 파일이 없으니 갈릴 자리도 없다.

    🔴 **하한선 미달인 날 이 함수가 `None`을 주면 호출자는 `deals.json`을 건드리지
    않는다.** 어제 파일이 그대로 남고 `generated`도 어제 시각이다. 그게 옳다 —
    **어제 데이터에 오늘 도장을 찍는 게 더 나쁘다**(2026-08-22 기획 합의).
    그 상태는 `meta.preserved`가 따로 말한다.

    `codes`: 이번에 발행된 노선 코드 집합. 딜의 `route` 필드가 **없는 노선을
    가리키지 않게** 한다 — 옛 경로에선 「HTML을 실제로 만든 노선」이었고,
    지금은 「v1에 실린 노선」이다. 같은 집합이다.
    """
    built = discover_data.build_deals_json(conn, codes)
    if built is None:
        return None
    return {**_envelope(generated), **built}


# -------------------------------------------------------------- 5) vocab.json

def _strip_comments(x):
    """`$comment` 키를 **중첩까지** 뺀다 — 파일 속 설명 문장이지 데이터가 아니다.

    최상위만 빼면 `tags.$comment`·`when.$comment`가 API로 나간다.
    """
    if isinstance(x, dict):
        return {k: _strip_comments(v) for k, v in x.items() if k != "$comment"}
    if isinstance(x, list):
        return [_strip_comments(v) for v in x]
    return x


def vocab_payload(generated):
    """참조 데이터 (`CONTRACT.md` §5, BE11).

    정본 `contract/v1/vocab.json`을 **그대로** 싣고 지역 표시명만 더한다.
    프론트에 남은 손 사본(상위 태그·when 칩·지역 표시명)을 URL로 바꾸려는 것이다 —
    백엔드가 어휘를 바꿨는데 칩이 옛 이름으로 남으면 **필터가 조용히 0건**이 된다.

    **발행 전용이다.** 어휘는 여기서 정하지 않는다 — 기획 결정 → `contract/` 수정.
    `region_name`은 `region` 순서로 만든다. 이름이 없는 코드가 있으면 `KeyError`로 터진다
    (조용히 빠지면 프론트가 코드를 그대로 보인다).
    """
    src = _strip_comments(json.loads(VOCAB_SRC.read_text(encoding="utf-8")))
    return {**_envelope(generated), **src,
            "region_name": {r: REGION_NAME[r] for r in src["region"]}}


# ------------------------------------------------------- 3)·4) routes/*.json

def route_payload(conn, origin, dest, generated):
    """노선 1개. 표본이 0이면 `None` — 그런 노선은 **응답 자체가 없다.**

    `min_samples`·`limit`을 끄고 부르는 게 이 함수의 요점이다.
    3건 미만인 달을 버리는 건 화면의 임계이지 **사실이 아니다.**
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
    """v1 5종(meta·deals·routes/index·routes/{code}·vocab)을 전부 쓴다. 반환: `(발행한 노선 수, 하한선 미달로 딜을 보존했나)`."""
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
    # 참조 데이터는 딜 보존과 무관하다 — 보존일에도 오늘 G 로 나간다(CONTRACT §5).
    _write("vocab.json", vocab_payload(generated))

    # 딜은 노선 **뒤에** 만든다 — `route` 필드가 이번에 실린 노선만 가리켜야 한다.
    deals = deals_payload(conn, {r["code"] for r in routes}, generated)
    if deals is not None:
        _write("deals.json", deals)
    preserved = deals is None

    # 건수는 **디스크에 실제로 있는 것**에서 센다. 보존된 날이면 어제 것의 건수다 —
    # 만들어진 것이 아니라 나가는 것을 세야 `meta`가 사실을 말한다.
    on_disk = V1 / "deals.json"
    cur = json.loads(on_disk.read_text(encoding="utf-8")) if on_disk.exists() else None
    _write("meta.json", meta_payload(
        {"deals": len(cur["deals"]) if cur else 0,
         "routes": len(routes),
         "origins": len(cur["origins"]) if cur else 0},
        preserved and cur is not None, generated))
    return len(routes), preserved


def warn_if_unpaid():
    """수익 시크릿이 없으면 **크게** 알린다 (BB30).

    산출물은 바꾸지 않는다 — 경고만이다. 없는 채로 도는 건 정당한 경우가 있고,
    막아야 할 건 그 결과물을 **모르고 커밋하는 것**이다. 마지막 방어선은
    `tests/test_affiliates.py`의 커밋본 검사다.
    """
    missing = affiliates.missing_secrets()
    if not missing:
        return False
    print("\n" + "!" * 68, file=sys.stderr)
    print("!! 제휴 시크릿이 없습니다: " + ", ".join(missing), file=sys.stderr)
    print("!! 이 빌드의 예약 링크에는 수수료 마커가 빠집니다 —", file=sys.stderr)
    print("!! 사이트는 멀쩡해 보이고 수익 경로만 사라집니다.", file=sys.stderr)
    print("!! docs/ 를 커밋하지 마십시오. (BACKEND.md BB30)", file=sys.stderr)
    print("!" * 68 + "\n", file=sys.stderr)
    return True


def _report_preserved(preserved):
    """산출물 보존 여부를 GitHub Actions에 알린다(BB18).

    발행은 성공으로 끝나야 한다 — 데이터는 커밋돼야 하니까. 대신 이 신호를
    워크플로 마지막 '상태 점검'이 읽어 잡을 실패로 표시하고, GitHub가 메일을 보낸다.
    로컬 실행에는 `GITHUB_OUTPUT`이 없으므로 아무 일도 하지 않는다.
    """
    out = os.environ.get("GITHUB_OUTPUT")
    if not out:
        return
    try:
        with open(out, "a", encoding="utf-8") as f:
            print(f"preserved={'true' if preserved else 'false'}", file=f)
    except OSError as e:                       # 신호 실패가 발행을 죽이면 안 된다
        print(f"  (GITHUB_OUTPUT 기록 실패: {e})")


def main():
    import db
    unpaid = warn_if_unpaid()
    conn = db.connect()
    n_routes, preserved = publish(conn)
    conn.close()
    deals = json.loads((V1 / "deals.json").read_text(encoding="utf-8"))["deals"]
    print(f"v1 발행: 노선 {n_routes}개 + 딜 {len(deals)}건"
          + ("  (딜은 하한선 미달로 어제 것 유지)" if preserved else ""))
    if unpaid:
        # 사람은 출력의 **끝**을 읽는다. 시작에서 외친 걸 여기서 한 번 더 말한다.
        print("  ⚠️ 수수료 마커 없이 만들어졌습니다 — docs/ 를 커밋하지 마십시오.",
              file=sys.stderr)
    _report_preserved(preserved)


if __name__ == "__main__":
    main()
