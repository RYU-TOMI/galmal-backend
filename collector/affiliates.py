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
from pathlib import Path

_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


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


def trip_deeplink(origin, dest, depart_date, return_date):
    """kr.trip.com 왕복 검색 딥링크를 tp.media 제휴 래퍼로 감싸 반환."""
    target = ("https://kr.trip.com/flights/showfarefirst"
              f"?dcity={origin.lower()}&acity={dest.lower()}"
              f"&ddate={depart_date}&rdate={return_date}"
              "&triptype=rt&class=y&quantity=1&locale=ko-KR&curr=KRW")
    return ("https://tp.media/r"
            f"?marker={_env('TP_MARKER')}&trs={_env('TP_TRIP_TRS')}"
            f"&p={_env('TP_TRIP_P')}&campaign_id={_env('TP_TRIP_CAMPAIGN')}"
            f"&u={urllib.parse.quote(target, safe='')}")


def booking_link(deal):
    """딜에 대한 (예약 URL, 예약처 이름) 반환. Trip.com 미설정 시 Aviasales 폴백."""
    if _trip_configured():
        return (trip_deeplink(deal["origin"], deal["destination"],
                              deal["depart_date"], deal["return_date"]),
                "Trip.com")
    return deal["link"], "Aviasales"
