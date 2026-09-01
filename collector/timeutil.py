# -*- coding: utf-8 -*-
"""시각 처리 단일 출처 — 특히 **API의 `found_at`이 UTC라는 사실**을 여기서만 안다.

이 모듈이 왜 있나:
  같은 사실을 두 곳에 적으면 하루는 하나가 틀린다. 실제로 그랬다 —
  `discover_data`는 `found_at`을 UTC로 올바르게 다뤘는데 `fetch_breadth`는
  naive 로컬 시각과 그냥 빼서 9시간을 부풀렸다(BB11). 이 프로젝트에서
  UTC/KST 혼동으로 잘못된 결론이 나온 게 세 번째였다.
  → 변환을 아는 곳을 **하나로** 만든다. 새 코드는 반드시 여기를 쓴다.

규칙 두 가지:
  1. **외부에서 들어온 시각은 경계에서 즉시 aware로 만든다.** naive인 채로
     돌아다니면 어딘가에서 다른 naive와 빼진다.
  2. **naive끼리 빼지 않는다.** 뺄셈은 aware끼리만 한다.

표시·기록은 KST(한국 전용 서비스), 계산은 aware라면 어느 시간대든 무방하다.
"""
from datetime import datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))

# Travelpayouts 응답의 `found_at`은 오프셋 없는 문자열이지만 **UTC**다.
# 근거(2026-08-22 실측): UTC로 해석해야 매일 가장 신선한 가격의 나이가 0h 부근으로
# 떨어진다 — 캐시가 방금 관측한 값을 돌려주는 자연스러운 그림이다. KST로 보면
# 최신값조차 8.8h 된 것이 되고, 최대 나이가 수집 필터 자신의 컷을 넘어 자기모순이 된다.
FOUND_AT_TZ = timezone.utc


def now_kst():
    """현재 시각 (KST, aware)."""
    return datetime.now(KST)


def today_utc():
    """**기계용 날짜** — `fetched_date` 같은 수집 라벨에 쓴다.

    `date.today()`는 실행 환경의 로컬 날짜라 크론(UTC 러너)과 로컬(KST)이
    서로 다른 값을 남긴다. 같은 명령이 환경에 따라 다른 데이터를 만드는 셈이다.
    UTC로 고정해 어디서 돌리든 같은 라벨이 나오게 한다.
    """
    return datetime.now(timezone.utc).date()


def today_kst():
    """**제품용 날짜** — "오늘 이후 출발"처럼 사용자 기준이 필요한 곳에 쓴다.

    한국 전용 서비스라 사용자의 '오늘'은 KST다. 새벽 3시 KST(전날 18시 UTC)에
    UTC 날짜로 거르면 한국 사용자에겐 이미 지난 항공편이 남는다.
    """
    return now_kst().date()


def parse_found_at(raw):
    """API의 `found_at` 문자열 → KST aware datetime. 변환 불가면 None.

    오프셋이 없으면 UTC로 간주한다. 이미 오프셋이 붙어 오면(향후 API 변경)
    그대로 존중한다 — UTC로 덮어쓰지 않는다.
    """
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(raw)
    except (TypeError, ValueError):
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=FOUND_AT_TZ)
    return dt.astimezone(KST)


def age_hours(raw, now=None):
    """`found_at` 이후 흐른 시간(시간 단위). 변환 불가면 None.

    시간 단위로 돌려주는 게 중요하다. `timedelta.days`는 **내림**이라
    "3일 이내"라고 쓰면 실제로는 95시간59분까지 통과한다(BB10).
    시간으로 재고 시간으로 비교하면 의도와 동작이 어긋나지 않는다.
    """
    seen = parse_found_at(raw)
    if seen is None:
        return None
    return ((now or now_kst()) - seen).total_seconds() / 3600
