# -*- coding: utf-8 -*-
"""도시·항공사 한글명, 지역 분류, 날짜 표기 — 사이트와 알림 메일이 공유."""
from datetime import date

import dests

WEEKDAY = "월화수목금토일"          # date.weekday(): 0=월
SQL_WEEKDAY = "일월화수목금토"      # strftime('%w'): 0=일

CITY = {
    "ICN": "인천", "GMP": "김포", "CJU": "제주",
    "NRT": "도쿄", "KIX": "오사카", "FUK": "후쿠오카", "OKA": "오키나와",
    "CTS": "삿포로", "NGO": "나고야", "TPE": "타이베이", "HKG": "홍콩",
    "BKK": "방콕", "DAD": "다낭", "SGN": "호치민", "HAN": "하노이",
    "MNL": "마닐라", "CEB": "세부", "SIN": "싱가포르", "KUL": "쿠알라룸푸르",
    "DPS": "발리", "GUM": "괌", "CDG": "파리", "LHR": "런던", "FCO": "로마",
    "BCN": "바르셀로나", "JFK": "뉴욕", "LAX": "로스앤젤레스", "SYD": "시드니",
}
AIRLINE = {
    "7C": "제주항공", "LJ": "진에어", "TW": "티웨이항공", "BX": "에어부산",
    "RS": "에어서울", "ZE": "이스타항공", "YP": "에어프레미아",
    "KE": "대한항공", "OZ": "아시아나항공", "VN": "베트남항공",
    "VJ": "비엣젯", "5J": "세부퍼시픽", "CA": "에어차이나", "MU": "중국동방항공",
    "CI": "중화항공", "BR": "에바항공", "CX": "캐세이퍼시픽", "TG": "타이항공",
    "SQ": "싱가포르항공", "MH": "말레이시아항공", "PR": "필리핀항공",
    "NH": "전일본공수", "JL": "일본항공", "ZG": "집에어",
}
def city(code):
    """IATA 코드 → 한글 도시명. 모르면 코드를 그대로 돌려준다.

    `CITY`에 없으면 `dests`로 넘긴다. 같은 지식(코드→한글명)이 두 사전에 있어서
    어긋났다 — 부산·대구가 `dests.ORIGINS`에만 있어 노선 페이지 제목이
    `"PUS → 도쿄"`로 나갔다(2026-09-01). 목적지도 `dests.DEST`가 84곳으로 더 넓다.

    `CITY`를 먼저 보는 이유는 노선 페이지가 오래 쓰던 표기를 지키기 위해서다
    (예: `DPS`는 `CITY`가 "발리", `dests`는 "덴파사르"). 새 코드를 여기 더하지 말고
    `dests`에 넣으면 자동으로 따라온다.
    """
    if code in CITY:
        return CITY[code]
    if code in dests.ORIGINS:
        return dests.ORIGINS[code]
    return dests.dest_name(code)


def airline_name(code):
    return AIRLINE.get(code, code)


def region_of(dest):
    """목적지 → 지역 코드. 사전에 없으면 `"etc"`.

    **이름도 코드도 `dests`가 정본이다.** 예전엔 여기 `REGION` 사전이 따로 있었는데
    초기 26개 노선만 담고 있어서 목적지를 넓힐 때마다 조용히 `"etc"`로 떨어졌고
    (89곳 중 59곳 불일치), 표시명 어휘까지 갈라져 **괌이 지도에서는 "휴양·섬",
    노선 페이지에서는 "국내·괌"** 이었다(BB26). 사전을 지우고 여기로 합쳤다.
    """
    entry = dests.DEST.get(dest)
    return entry[2] if entry else "etc"


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
