# -*- coding: utf-8 -*-
"""수집 대상 노선과 특가 판정 기준 설정"""

# (출발지, 도착지) IATA 코드. 2026-07-09 Travelpayouts 커버리지 검증 완료 노선 중심.
ROUTES = [
    # 일본
    ("ICN", "NRT"), ("ICN", "KIX"), ("ICN", "FUK"), ("ICN", "OKA"),
    ("ICN", "CTS"), ("ICN", "NGO"),
    # 중화권/동남아
    ("ICN", "TPE"), ("ICN", "HKG"), ("ICN", "BKK"), ("ICN", "DAD"),
    ("ICN", "SGN"), ("ICN", "HAN"), ("ICN", "MNL"), ("ICN", "CEB"),
    ("ICN", "SIN"), ("ICN", "KUL"), ("ICN", "DPS"),
    # 휴양지/기타
    ("ICN", "GUM"),
    # 장거리
    ("ICN", "CDG"), ("ICN", "LHR"), ("ICN", "FCO"), ("ICN", "BCN"),
    ("ICN", "JFK"), ("ICN", "LAX"), ("ICN", "SYD"),
    # 국내
    ("GMP", "CJU"),
]

CURRENCY = "krw"

# 특가 판정: 해당 노선 최근 BASELINE_DAYS일 가격 중앙값 대비 DEAL_RATIO 이하이면 특가
BASELINE_DAYS = 30
DEAL_RATIO = 0.65

# 노선·유형(직항/경유)별 최소 표본 수 (이보다 적으면 판정 보류)
MIN_SAMPLES = 10
