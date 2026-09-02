# -*- coding: utf-8 -*-
"""제휴 예약 링크 빌더.

한국 사용자 UX를 위해 기본 예약처는 Trip.com(한국어) — Travelpayouts 계정에서
Trip.com 프로그램 가입 후 아래 4개 값을 .env / GitHub Secrets에 넣으면 활성화된다.
(TP 대시보드 → 도구 → 링크 생성기에서 만든 링크의 파라미터를 그대로 옮기면 됨)

  TP_MARKER=마커(제휴 ID)
  TP_TRIP_TRS=trs 값
  TP_TRIP_P=p 값
  TP_TRIP_CAMPAIGN=campaign_id 값

값이 없으면 Aviasales 원본 딥링크로 폴백한다 (사이트가 깨지지 않도록).
"""
import os
import urllib.parse
from datetime import date
from pathlib import Path

_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


def _ddmm(iso):
    d = date.fromisoformat(iso)
    return f"{d.day:02d}{d.month:02d}"


def _yymmdd(iso):
    d = date.fromisoformat(iso)
    return f"{d.year % 100:02d}{d.month:02d}{d.day:02d}"


def _yyyymmdd(iso):
    d = date.fromisoformat(iso)
    return f"{d.year:04d}{d.month:02d}{d.day:02d}"


_KR_AIRPORTS = {"ICN", "GMP", "PUS", "TAE", "CJU"}


def _env(name):
    val = os.environ.get(name)
    if val:
        return val.strip()
    if _ENV_FILE.exists():
        for line in _ENV_FILE.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith(f"{name}="):
                return line.split("=", 1)[1].strip()
    return None


def _trip_configured():
    return all(_env(k) for k in
               ("TP_MARKER", "TP_TRIP_TRS", "TP_TRIP_P", "TP_TRIP_CAMPAIGN"))


def _trip_target(origin, dest, depart_date, return_date):
    base = ("https://kr.trip.com/flights/showfarefirst"
            f"?dcity={origin.lower()}&acity={dest.lower()}"
            f"&ddate={depart_date}&class=y&quantity=1&locale=ko-KR&curr=KRW")
    if return_date:
        return base + f"&rdate={return_date}&triptype=rt"
    return base + "&triptype=ow"


def trip_link(origin, dest, depart_date, return_date=None):
    """kr.trip.com(한국어) 검색 링크. 제휴 설정 시 tp.media 래퍼로 감싸 수수료 발생,
    미설정 시 순수 Trip.com 링크(수수료 없음, 사용자 UX는 동일하게 한국어)."""
    target = _trip_target(origin, dest, depart_date, return_date)
    if _trip_configured():
        return ("https://tp.media/r"
                f"?marker={_env('TP_MARKER')}&trs={_env('TP_TRIP_TRS')}"
                f"&p={_env('TP_TRIP_P')}&campaign_id={_env('TP_TRIP_CAMPAIGN')}"
                f"&u={urllib.parse.quote(target, safe='')}")
    return target


def booking_link(deal):
    """딜 dict → (예약 URL, 예약처 이름). 항상 Trip.com 한국어. (하위호환)"""
    return (trip_link(deal["origin"], deal["destination"],
                      deal.get("depart_date"), deal.get("return_date")),
            "Trip.com")


# ---------------------------------------------------------------- 비교 패널
# 특정 예약처를 밀지 않고 여러 곳을 나란히 — 사용자가 최저가를 직접 고른다.
# 수수료 되는 곳(Aviasales)엔 마커 자동, 나머지는 순수 검색 링크(한국어 UX 우선).

def aviasales_link(origin, dest, depart_date, return_date=None):
    """Aviasales 검색 딥링크 + 우리 마커(승인된 유일 수수료원). 영어 UX."""
    seg = f"{origin.upper()}{_ddmm(depart_date)}{dest.upper()}"
    if return_date:
        seg += _ddmm(return_date)
    url = f"https://www.aviasales.com/search/{seg}1"
    marker = _env("TP_MARKER")
    return url + (f"?marker={marker}" if marker else "")


def skyscanner_link(origin, dest, depart_date, return_date=None):
    """스카이스캐너 KR — 전체 비교(메타)·한국어."""
    path = f"{origin.lower()}/{dest.lower()}/{_yymmdd(depart_date)}/"
    if return_date:
        path += f"{_yymmdd(return_date)}/"
    return (f"https://www.skyscanner.co.kr/transport/flights/{path}"
            "?adults=1&currency=KRW&market=KR&locale=ko-KR")


def google_flights_link(origin, dest, depart_date, return_date=None):
    """구글 항공권 — 중립·한국어. q 기반 best-effort 프리필."""
    q = f"{origin.upper()} to {dest.upper()} on {depart_date}"
    if return_date:
        q += f" through {return_date}"
    return ("https://www.google.com/travel/flights?hl=ko&curr=KRW&q="
            + urllib.parse.quote(q))


def naver_link(origin, dest, depart_date, return_date=None):
    """네이버 항공권 — 한국인 최다 이용·자체 비교. 국내선/국제선 자동 구분."""
    o, d = origin.upper(), dest.upper()
    kind = "domestic" if d in _KR_AIRPORTS else "international"
    path = f"{o}-{d}-{_yyyymmdd(depart_date)}"
    if return_date:
        path += f"/{d}-{o}-{_yyyymmdd(return_date)}"
    return f"https://flight.naver.com/flights/{kind}/{path}?adult=1&fareType=Y"


def compare_links(origin, dest, depart_date, return_date=None):
    """예약처 비교 목록 [{name, tag, ad, url}] — 한국어 메타/OTA 우선.
    Aviasales(영어)는 수수료 마커(TP_MARKER)가 있을 때만 = 실제로 수익 날 때만 노출.
    한국인 전용 사이트라 마커 없으면 영어 예약처는 숨긴다.

    `ad` — **이 링크로 예약하면 우리에게 수수료가 오는가.** 화면의 "(광고)" 고지가
    이 값으로 결정된다(프론트 요청 2026-09-02, 정보통신망법·공정위 고지 의무).

    왜 필드로 주나: 프론트가 이름("Aviasales")·순서(맨 뒤)·URL 모양("marker=")으로
    추측하면 **제휴 구성이 바뀌는 날 조용히 틀려진다.** 판정을 아는 건 여기뿐이므로
    여기서 단언한다. 이 저장소는 같은 실수를 이미 두 번 했다(`d`가 공항 코드인 줄
    알았던 것, `MAX_AGE_DAYS`가 일 단위인 줄 알았던 것).

    **Trip.com도 승인되면 수수료가 붙는다.** `_trip_configured()`가 참이면
    `trip_link()`가 tp.media 래퍼로 감싸므로 그때부터 제휴 링크다. Aviasales만
    하드코딩하지 않는 이유가 이것이다 — 승인되는 날 고지가 저절로 따라붙는다.
    """
    links = [
        {"name": "스카이스캐너", "tag": "전체 비교", "ad": False,
         "url": skyscanner_link(origin, dest, depart_date, return_date)},
        {"name": "네이버 항공권", "tag": "한국 인기", "ad": False,
         "url": naver_link(origin, dest, depart_date, return_date)},
        {"name": "구글 항공권", "tag": "중립", "ad": False,
         "url": google_flights_link(origin, dest, depart_date, return_date)},
        {"name": "Trip.com", "tag": "한국어", "ad": _trip_configured(),
         "url": trip_link(origin, dest, depart_date, return_date)},
    ]
    if _env("TP_MARKER"):
        links.append({"name": "Aviasales", "tag": "영어·수수료", "ad": True,
                      "url": aviasales_link(origin, dest, depart_date, return_date)})
    return links
