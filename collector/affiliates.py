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
import urllib.parse
from datetime import date

import env


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
    """`env.get()`의 얇은 별칭. 이 모듈이 `.env`를 직접 읽던 흔적이다(BE18에서 한 곳으로 모았다)."""
    return env.get(name)


# 🔴 **운영에 반드시 있어야 하는** 시크릿. 없으면 링크가 조용히 빠진다.
#
# Trip.com 쪽(`TP_TRIP_*`)은 여기 넣지 않는다 — 아직 제휴 승인 전이라
# **없는 게 정상**이다. 정상 상태에 경고를 띄우면 사람이 경고를 무시하는 법을
# 배우고, 정작 진짜일 때 안 읽는다. 승인되면(BE5) 그때 여기 넣는다.
REQUIRED_SECRETS = ("TP_MARKER",)


def missing_secrets():
    """설정되지 않은 수익 시크릿 목록 (BB30).

    없으면 예외가 나는 게 아니라 **링크가 그냥 빠진다** — 사이트는 멀쩡히 뜨고
    수수료 경로만 사라진다. 2026-09-08에 프론트가 `index.html` 충돌을
    `CLAUDE.md`의 「재빌드로 해결」 절차대로 풀다가 딜 125건 전부에서
    Aviasales 링크를 날릴 뻔했다(커밋 직전 복구).

    **함정은 절차가 아니라 여기다.** 충돌 해결 규칙은 재빌드 환경에 시크릿이
    있다고 가정하는데, 크론(Actions)은 있고 로컬은 사람마다 다르다.
    발행이 조용히 통과하면 아무도 못 알아챈다 → `publish.py`가 이걸 보고 외친다.
    """
    return [k for k in REQUIRED_SECRETS if not _env(k)]


def _trip_configured():
    return all(_env(k) for k in
               ("TP_MARKER", "TP_TRIP_TRS", "TP_TRIP_P", "TP_TRIP_CAMPAIGN"))


def _trip_target(origin, dest, depart_date, return_date, adults=1):
    base = ("https://kr.trip.com/flights/showfarefirst"
            f"?dcity={origin.lower()}&acity={dest.lower()}"
            f"&ddate={depart_date}&class=y&quantity={adults}&locale=ko-KR&curr=KRW")
    if return_date:
        return base + f"&rdate={return_date}&triptype=rt"
    return base + "&triptype=ow"


def trip_link(origin, dest, depart_date, return_date=None, adults=1):
    """kr.trip.com(한국어) 검색 링크. 제휴 설정 시 tp.media 래퍼로 감싸 수수료 발생,
    미설정 시 순수 Trip.com 링크(수수료 없음, 사용자 UX는 동일하게 한국어).

    인원은 `quantity`. 2026-09-22 실측: `quantity=2` → 「성인 2명 · 일반석」.
    ⚠️ 제휴 래퍼는 target 을 **URL 인코딩해서** 감싼다 — `_PAX_TOKEN` 이 영숫자인 이유가 이것이다.
    """
    target = _trip_target(origin, dest, depart_date, return_date, adults)
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

def aviasales_link(origin, dest, depart_date, return_date=None, adults=1):
    """Aviasales 검색 딥링크 + 우리 마커(승인된 유일 수수료원). 영어 UX.

    인원은 **파라미터가 아니라 경로 끝 숫자**다(`…TYO08122` = 2명). 2026-09-22 실측: 「2 pax」.
    """
    seg = f"{origin.upper()}{_ddmm(depart_date)}{dest.upper()}"
    if return_date:
        seg += _ddmm(return_date)
    url = f"https://www.aviasales.com/search/{seg}{adults}"
    marker = _env("TP_MARKER")
    return url + (f"?marker={marker}" if marker else "")


def skyscanner_link(origin, dest, depart_date, return_date=None, adults=1):
    """스카이스캐너 KR — 전체 비교(메타)·한국어.

    🔴 인원 파라미터는 `adults` 가 아니라 **`adultsv2`** 다(BB42). 2026-09-22 브라우저 실측:
    `?adults=2` → 화면 「성인 **1명**」(**이름을 읽지 않는다**) · `?adultsv2=2` → 「여행자 2명」.
    예전엔 `adults=1` 을 보냈고 **기본값이 1인이라 결과가 우연히 맞아** 아무도 못 봤다.
    """
    path = f"{origin.lower()}/{dest.lower()}/{_yymmdd(depart_date)}/"
    if return_date:
        path += f"{_yymmdd(return_date)}/"
    return (f"https://www.skyscanner.co.kr/transport/flights/{path}"
            f"?adultsv2={adults}&currency=KRW&market=KR&locale=ko-KR")


def google_flights_link(origin, dest, depart_date, return_date=None, adults=1):
    """구글 항공권 — 중립·한국어. q 기반 best-effort 프리필.

    인원 **파라미터가 없다** — 자연어 질의가 받는다. 2026-09-22 실측: `for 2 adults` → 「성인 2명의
    세금·수수료 포함」, `for 1 adults`(비문이지만) → 「성인 1명」. 그래서 1인에도 같은 문구를 넣어
    `pax_url` 의 `{n}`→`1` 이 `url` 과 바이트가 같게 만든다(계약 §links[] 의 보장 ①).
    """
    q = f"{origin.upper()} to {dest.upper()} on {depart_date}"
    if return_date:
        q += f" through {return_date}"
    q += f" for {adults} adults"
    return ("https://www.google.com/travel/flights?hl=ko&curr=KRW&q="
            + urllib.parse.quote(q))


def naver_link(origin, dest, depart_date, return_date=None, adults=1):
    """네이버 항공권 — 한국인 최다 이용·자체 비교. 국내선/국제선 자동 구분.

    인원 파라미터는 **단수형 `adult`** 다(복수형이 아니다). 2026-09-22 실측: `adult=2` → 「성인 2명」.
    """
    o, d = origin.upper(), dest.upper()
    kind = "domestic" if d in _KR_AIRPORTS else "international"
    path = f"{o}-{d}-{_yyyymmdd(depart_date)}"
    if return_date:
        path += f"/{d}-{o}-{_yyyymmdd(return_date)}"
    return f"https://flight.naver.com/flights/{kind}/{path}?adult={adults}&fareType=Y"


# 🔑 `pax_url` 을 만들 때 인원 자리에 잠깐 끼우는 표식 (계약 §links[] · DECISIONS 2026-09-22 (4)).
#
# **영숫자여야 한다.** 구글 `q` 와 Trip.com 제휴 래퍼는 URL 을 **인코딩해서** 감싸는데,
# `{n}` 을 그대로 넣으면 `%7Bn%7D` 가 되어 **인코딩 안에 묻힌다** — 소비자가 `{n}` 을 찾지 못한다.
# 영숫자 표식은 `quote()` 가 건드리지 않으므로, 인코딩이 끝난 뒤에 `{n}` 으로 바꾸면 토큰이 바깥에 남는다.
_PAX_TOKEN = "PAXPLACEHOLDER"

# 예약처가 인원을 어디서 받는지는 **링크를 만드는 쪽만 안다**(2026-09-22 브라우저 실측):
#   스카이스캐너 adultsv2= · 네이버 adult= · Trip.com quantity= · 구글 q 자연어 · Aviasales 경로 끝 숫자
# 소비자가 이름·순서로 추측하면 `ad` 때의 추측이 다시 생긴다 — 그래서 **완성된 URL 한 벌로** 준다.
_BUILDERS = (
    ("스카이스캐너", "전체 비교", False, skyscanner_link),
    ("네이버 항공권", "한국 인기", False, naver_link),
    ("구글 항공권", "중립", False, google_flights_link),
    ("Trip.com", "한국어", None, trip_link),          # ad 는 제휴 설정 여부로 정해진다
)


def compare_links(origin, dest, depart_date, return_date=None):
    """예약처 비교 목록 `[{name, tag, ad, url, pax_url}]` — 한국어 메타/OTA 우선.
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

    `pax_url` — **인원 `{n}` 명으로 여는 URL 한 벌** (계약 §links[], 2026-09-22).
    같은 빌더를 인원 표식으로 한 번 더 불러 만들기 때문에 **`{n}`→`1` 은 `url` 과 반드시 같다** —
    두 필드가 갈릴 자리를 구조로 없앤 것이다(`tests/test_affiliates.py` 가 그 동일성을 잠근다).
    지금은 다섯 곳 모두 인원을 받으므로 `null` 이 나오지 않는다. 못 받는 곳이 생기면 그때 `None` 을 넣는다.
    """
    trip_ad = _trip_configured()
    marker = _env("TP_MARKER")

    def build(adults):
        out = [fn(origin, dest, depart_date, return_date, adults)
               for _, _, _, fn in _BUILDERS]
        if marker:
            out.append(aviasales_link(origin, dest, depart_date, return_date, adults))
        return out

    ones, toks = build(1), build(_PAX_TOKEN)
    meta = [(n, t, trip_ad if ad is None else ad) for n, t, ad, _ in _BUILDERS]
    if marker:
        meta.append(("Aviasales", "영어·수수료", True))

    links = []
    for (name, tag, ad), url, tok in zip(meta, ones, toks):
        assert tok.count(_PAX_TOKEN) == 1, f"{name}: 인원 표식이 {tok.count(_PAX_TOKEN)}곳"
        links.append({"name": name, "tag": tag, "ad": ad, "url": url,
                      "pax_url": tok.replace(_PAX_TOKEN, "{n}")})
    return links
