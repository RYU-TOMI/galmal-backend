# -*- coding: utf-8 -*-
"""목업 빌더 공용 포맷·규칙.

같은 사실을 여러 빌더에 각각 적으면 하나는 틀린다(백엔드 timeutil 교훈).
날짜 표기·태그 고르기·도장 티어처럼 **확정된 규칙**은 여기 한 곳에만 둔다.
소유: 기획 세션.
"""
from datetime import date

# ── 통제 어휘 (CONTRACT.md `tags` 절과 같아야 한다) ──────────────
TOP = ["해변", "도시", "미식", "자연", "문화", "온천"]
SUB = {"리조트", "스노클링", "서핑", "섬", "야경", "쇼핑", "마천루", "골목",
       "야시장", "길거리음식", "화산", "트레킹", "사막", "폭포", "사원", "유적", "고성", "미술관"}

# ── 도장 티어 (SPEC.md §CH3, 2026-09-01 유지 확정) ──────────────
TIERS = [(35, "t3"), (25, "t2"), (15, "t1")]

WD = "월화수목금토일"


def tier(d):
    v = d.get("discount", 0)
    for lo, t in TIERS:
        if v >= lo:
            return t
    return None


def direct(d):
    """직항 배지는 중·장거리에만. 근거리 직항은 75%라 당연해서 배지가 아니다."""
    return d["transfers"] == 0 and d["haul"] != "short"


def card_tags(tags):
    """표시할 태그 = 하위 전부 + 상위 1개(하위 없으면 상위 2개), 최대 4개."""
    s = [t for t in tags if t in SUB]
    tp = [t for t in tags if t in TOP]
    return (s + tp[:1] if s else tp[:2])[:4]


def money(v):
    return "{:,}".format(v)


def _d(s):
    y, m, dd = (int(x) for x in s.split("-"))
    return date(y, m, dd)


def daterange(dep, ret):
    """날짜 주 라인 — `9/8(화) → 9/16(수)`. 편도면 `9/8(화) 편도`.

    ⚠️ `ret`은 null일 수 있다(CONTRACT.md: "편도면 null").
       요일은 날짜만으로 정해지므로 타임존 문제가 없다.
    """
    if not dep:
        return ""
    a = _d(dep)
    head = "%d/%d<span class=\"wd\">(%s)</span>" % (a.month, a.day, WD[a.weekday()])
    if not ret:
        return head + '<span class="wd"> 편도</span>'
    b = _d(ret)
    return "%s <span class=\"arw\">&rarr;</span> %d/%d<span class=\"wd\">(%s)</span>" % (
        head, b.month, b.day, WD[b.weekday()])


def datesub(d):
    """날짜 보조 라인 — `8박9일 · 이번 주`."""
    bits = [x for x in (d.get("nights", ""), d.get("when", "")) if x]
    return " &middot; ".join(bits)


# 날짜 두 줄에 공통으로 쓰는 CSS. 빌더마다 색·크기는 덧씌운다.
DATE_CSS = """
.dmain{font-variant-numeric:tabular-nums;font-weight:800}
.dmain .wd{font-weight:700;color:var(--sub)}
.dmain .arw{color:var(--sub);margin:0 1px;font-weight:700}
.dsub{font-variant-numeric:tabular-nums;font-weight:700;color:var(--sub)}
"""
