# -*- coding: utf-8 -*-
"""표시 포맷 — 날짜·월·요일을 사람이 읽는 문자열로.

**`collector/labels.py` 에서 포맷 부분만 인수했다**(레포 분리, SPLIT.md M2).

`labels.py` 는 두 성격이 섞여 있어서 통째로 옮기지 않았다:

| 무엇 | 어디로 | 왜 |
|---|---|---|
| `city()` `airline_name()` `region_of()` `CITY` `AIRLINE` | **백엔드에 남는다** | 참조 데이터다. 계약이 `o_name`·`d_name`·`airlines[].name`·`region` 으로 직접 준다 |
| `fmt_date()` `fmt_month()` `WEEKDAY` `SQL_WEEKDAY` | **여기** | 표시 문자열이다. 「2026-09」를 「9월」로 읽는 건 화면의 일이다(P7) |

그래서 이 파일은 `dests` 를 import 하지 않는다 — 프론트는 백엔드 모듈을 안 본다.

🔴 **`fmt_month()` 는 연도를 버린다**(BB31). `'2027-02'` → `'2월'`.
지금은 안 깨진다 — 계약의 `months` 창이 미래만 남기고, 프론트가 재현하는 `LIMIT 10`
(월 오름차순 앞 10개)이 버킷을 12개월 안에 묶어 같은 월 이름이 두 번 안 나온다.
**여유는 정확히 1개다**(실측 2026-09-08: 최대 `ICN-DPS` 등 12개, 2026-09~2027-08).

**이전 중에는 고치지 않는다** — 현행 화면을 재현해야 M2 T5 동등성 증명이 성립한다.
다만 「안 깨진다」가 「안 헷갈린다」는 뜻은 아니다. 2026-09-08 하루에 **세션 둘이 같은
라벨을 과거로 잘못 읽었다**(`ICN-KUL` 6월 = 2027-06, `ICN-LAX` 2월 = 2027-02).
사람도 「다음에 오는 2월」로 읽으려면 오늘이 몇 월인지 세어야 한다. `COPY.md` §6.
월 버킷 상한을 푸는 결정과 **같이** 다룬다 — 상한을 풀면 그날 바로 깨진다.
"""
from datetime import date

WEEKDAY = "월화수목금토일"          # date.weekday(): 0=월
SQL_WEEKDAY = "일월화수목금토"      # strftime('%w'): 0=일 — 계약 `weekdays[].wd` 가 이 규약이다


def fmt_date(iso):
    """'2026-07-18' -> '7.18(토)'"""
    try:
        d = date.fromisoformat(iso)
        return f"{d.month}.{d.day}({WEEKDAY[d.weekday()]})"
    except (ValueError, TypeError):
        return iso or ""


def fmt_month(ym):
    """'2026-08' -> '8월'"""
    try:
        return f"{int(ym.split('-')[1])}월"
    except (ValueError, IndexError, AttributeError):
        return ym or ""


def weekday_name(wd):
    """계약 `weekdays[].wd`(0=일 … 6=토) -> '월'.

    🔴 **배열 순서를 믿지 않는다.** 응답은 월요일부터 정렬되어 오지만 그건 편의고,
    정본은 `wd` 값이다(`CONTRACT.md` §v1). 순서에 기대면 백엔드가 정렬을 바꾸는 날
    조용히 요일이 어긋난다 — 화면은 멀쩡해 보이고 값만 틀린다.
    """
    try:
        return SQL_WEEKDAY[int(wd)]
    except (ValueError, TypeError, IndexError):
        return str(wd)
