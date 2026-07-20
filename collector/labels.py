# -*- coding: utf-8 -*-
"""도시·항공사 한글명, 지역 분류, 날짜 표기 — 사이트와 알림 메일이 공유."""
from datetime import date

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
REGION = {
    "NRT": "jp", "KIX": "jp", "FUK": "jp", "OKA": "jp", "CTS": "jp", "NGO": "jp",
    "TPE": "cn", "HKG": "cn",
    "BKK": "sea", "DAD": "sea", "SGN": "sea", "HAN": "sea", "MNL": "sea",
    "CEB": "sea", "SIN": "sea", "KUL": "sea", "DPS": "sea",
    "CDG": "eu", "LHR": "eu", "FCO": "eu", "BCN": "eu",
    "JFK": "am", "LAX": "am", "SYD": "am",
    "GUM": "dom", "CJU": "dom",
}
REGION_NAME = {"jp": "일본", "sea": "동남아", "cn": "중화권", "eu": "유럽",
               "am": "미주·대양주", "dom": "국내·괌", "etc": "기타"}
REGION_CHIPS = [("all", "전체"), ("jp", "일본"), ("sea", "동남아"), ("cn", "중화권"),
                ("eu", "유럽"), ("am", "미주·대양주"), ("dom", "국내·괌")]


def city(code):
    return CITY.get(code, code)


def airline_name(code):
    return AIRLINE.get(code, code)


def region_of(dest):
    return REGION.get(dest, "etc")


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
