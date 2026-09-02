# -*- coding: utf-8 -*-
"""홈 화면 장면 조립 — home.html과 dock.html이 같은 함수를 쓴다.

같은 화면을 두 곳에서 그리면 하나는 틀어진다(백엔드 timeutil 교훈).
시각 규칙은 _app.py, 포맷·판정은 _fmt.py에 있다.
소유: 기획 세션.
"""
import os, sys

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
from _app import SW, SH, BOXES, dock_html, panel_filter, claim, record
from _fmt import tier, direct, card_tags, money, daterange, datesub

LAND_BLOBS = [(70, 90, 300, 250), (300, 60, 260, 200), (180, 330, 300, 240),
              (470, 250, 240, 210), (560, 430, 220, 170), (40, 400, 180, 160)]


def make_scene(D, origin="SEL", hauls=("short", "medium")):
    """실제 좌표를 투영하고 히어로·열어 둘 딜을 고른다."""
    ALL = sorted([x for x in D["deals"] if x["o"] == origin], key=lambda x: x["price"])
    O = D["origins"][origin]
    STAGE = [d for d in ALL if d["haul"] in hauls]

    lons = [d["lon"] for d in STAGE] + [O["lon"]]
    lats = [d["lat"] for d in STAGE] + [O["lat"]]
    lon0, lat0 = (min(lons) + max(lons)) / 2.0, (min(lats) + max(lats)) / 2.0
    pad = 74
    K = min((SW - pad * 2) / max(1e-6, max(lons) - min(lons)),
            (SH - pad * 2) / max(1e-6, max(lats) - min(lats)))

    def proj(lon, lat):
        return (SW / 2.0 + (lon - lon0) * K, SH / 2.0 - (lat - lat0) * K)

    OX, OY = proj(O["lon"], O["lat"])
    for d in STAGE:
        d["_x"], d["_y"] = proj(d["lon"], d["lat"])

    HERO = ALL[0]

    def fits(d):
        """상세 카드가 무대 밖으로 안 넘치는 자리인가.

        예약처가 5곳이 되며 상세가 약 432px가 됐다(2026-09-01). 핀은 아래쪽 72%,
        카드 최대 높이는 핀 y - 16이고 넘치면 카드 안에서 스크롤한다(SPEC §CH4).
        """
        return 130 < d["_x"] < SW - 130 and SH * 0.62 < d["_y"] < SH - 30

    POOL = [d for d in STAGE if d is not HERO]
    OPEN = next((d for d in POOL if tier(d) and len(card_tags(d["tags"])) >= 3 and fits(d)),
                next((d for d in POOL if tier(d) and fits(d)),
                     next((d for d in POOL if fits(d)), POOL[0])))

    lands = "".join(
        '<div class="land" style="left:%dpx;top:%dpx;width:%dpx;height:%dpx"></div>' % g
        for g in LAND_BLOBS)

    arcs = ""
    for d in STAGE:
        mx = (OX + d["_x"]) / 2.0
        my = (OY + d["_y"]) / 2.0 - abs(d["_x"] - OX) * 0.17 - 16
        op, w = (".72", "1.7") if d is OPEN else (".15", "1")
        arcs += ('<path d="M%.1f,%.1f Q%.1f,%.1f %.1f,%.1f" fill="none" stroke="#F2603F" '
                 'stroke-width="%s" opacity="%s"/>' % (OX, OY, mx, my, d["_x"], d["_y"], w, op))

    return {"ALL": ALL, "STAGE": STAGE, "HERO": HERO, "OPEN": OPEN, "FEED": ALL[1:9],
            "OX": OX, "OY": OY, "LANDS": lands, "ARCS": arcs, "ONAME": O["name"]}


def covered(ctx, box):
    """가려지는 핀 개수 — 넓이가 아니라 핀으로 잰다. 지도는 핀을 보여주려고 있다."""
    if not box:
        return 0
    l, t, r, b = box
    return sum(1 for d in ctx["STAGE"] if l <= d["_x"] <= r and t <= d["_y"] <= b)


def pins(ctx, box):
    l, t, r, b = box if box else (-1, -1, -1, -1)
    OX, OY = ctx["OX"], ctx["OY"]
    out = ('<span class="pin orig" style="left:%.1fpx;top:%.1fpx"></span>'
           '<span class="plab orig" style="left:%.1fpx;top:%.1fpx">%s</span>'
           % (OX, OY, OX, OY, ctx["ONAME"]))
    for d in ctx["STAGE"]:
        hid = bool(box) and (l <= d["_x"] <= r and t <= d["_y"] <= b)
        cls = " on" if d is ctx["OPEN"] else (" hid" if hid else "")
        out += '<span class="pin%s" style="left:%.1fpx;top:%.1fpx"></span>' % (cls, d["_x"], d["_y"])
    for d in ctx["STAGE"]:
        hid = bool(box) and (l <= d["_x"] <= r and t <= d["_y"] <= b)
        if (d.get("tier") == "major" or d is ctx["OPEN"]) and not hid:
            out += ('<span class="plab" style="left:%.1fpx;top:%.1fpx">%s</span>'
                    % (d["_x"], d["_y"], d["ko"]))
    return out


def small_card(d, on=False):
    """작은 카드 — 태그 없음. 주장은 하나(도장 우선, 없으면 신기록)."""
    bdg = '<span class="bdg">&#9992; 직항</span>' if direct(d) else ""
    return ('<div class="fcard%s"><div class="thumb"></div><div class="fbody">'
            '<div class="frow"><span class="fcity">%s</span>%s</div>'
            '<div class="prow"><span class="price">%s<small>원</small></span>%s</div>'
            '<div class="dmain">%s</div><div class="dsub">%s</div></div></div>'
            % (" on" if on else "", d["ko"], claim(d), money(d["price"]), bdg,
               daterange(d.get("dep"), d.get("ret")), datesub(d)))


def hero_card(d):
    tags = "".join('<span class="phtag">%s</span>' % t for t in card_tags(d["tags"]))
    bdg = '<span class="bdg">&#9992; 직항</span>' if direct(d) else ""
    return ('<div class="fcard hero"><div class="ph"><span class="pick">오늘의 발견</span>'
            '<div class="phtags">%s</div><span class="cityover">%s</span></div>'
            '<div class="hb"><div class="prow" style="margin-top:0">'
            '<span class="price">%s<small>원</small></span>%s</div>'
            '<div class="dmain">%s</div><div class="dsub">%s</div>'
            '<div style="margin-top:7px">%s</div></div></div>'
            % (tags, d["ko"], money(d["price"]), claim(d),
               daterange(d.get("dep"), d.get("ret")), datesub(d), bdg))


def detail(d):
    """확장 상세 — 카드와 달리 도장과 신기록을 **둘 다** 보인다(SPEC §CH3)."""
    tags = "".join('<span class="phtag">%s</span>' % t for t in card_tags(d["tags"]))
    bdg = '<span class="bdg">&#9992; 직항</span>' if direct(d) else ""
    t = tier(d)
    stamp = ('<span class="stamp %s">%d%%&darr;</span>' % (t, d["discount"])) if t else ""
    med = d.get("median")
    if med and med > d["price"]:
        bars = ('<div class="cmp"><span style="width:36px;color:var(--sub)">평소</span>'
                '<span class="bar mut"><i style="width:100%%"></i></span><b>%s원</b></div>'
                '<div class="cmp"><span style="width:36px;font-weight:800">지금</span>'
                '<span class="bar"><i style="width:%d%%"></i></span><b>%s원</b></div>'
                % (money(med), int(100.0 * d["price"] / med), money(d["price"])))
    else:
        # CONTRACT: median은 null일 수 있다. 없는 걸 지어내지 않는다.
        bars = ('<div style="font-size:.56rem;color:var(--sub);line-height:1.5">'
                '아직 이 노선의 평소 시세를 모아두지 못했어요</div>')
    rec = ('<div class="rec2">&darr; %d일 중 최저가예요</div>' % d.get("obs_days", 0)) if record(d) else ""
    links = (d.get("links") or [])
    lnk = "".join('<div class="lnk"><span>%s</span><span class="p">%s원</span></div>'
                  % (l.get("name", "비교 사이트"), money(l.get("price", d["price"])))
                  for l in links) \
        or ('<div class="lnk"><span>비교 사이트</span><span class="p">%s원</span></div>'
            % money(d["price"]))
    return ('<div class="det"><div class="ph"><span class="closex">&times;</span>'
            '<div class="phtags">%s</div><span class="cityover">%s</span></div><div class="db">'
            '<div class="prow" style="margin-top:0">'
            '<span class="price" style="font-size:1.08rem">%s<small>원</small></span>%s</div>'
            '<div class="prow" style="margin-top:3px">'
            '<span class="dmain" style="margin-top:0">%s</span>%s</div>'
            '<div class="dsub" style="margin-top:3px">%s</div>'
            '<div class="dsec">평소 시세와 비교</div>%s%s'
            '<div class="dsec">어디가 제일 싼지 비교해보세요</div>%s'
            '<div class="go">갈래 &rarr; 예약처로</div>'
            '<div class="ad">위 가격은 발견가(스캔 시점) · 실시간 최저가는 각 사이트에서 확인하세요<br>'
            '일부는 예약 시 수수료 (광고)</div></div></div>'
            % (tags, d["ko"], money(d["price"]), stamp,
               daterange(d.get("dep"), d.get("ret")), bdg, datesub(d), bars, rec, lnk))


def app(ctx, kind, badges=""):
    """홈 셸 전체. kind는 도크 종류(F0~F3)."""
    box = BOXES[kind]
    o = ctx["OPEN"]
    return ('<div class="app">' + badges +
            '<div class="hdr"><span class="logo">갈래<i>말래</i></span>'
            '<span class="nav"><span class="a">발견</span><span class="m">노선별</span></span>'
            '<span class="origin">%s 출발 &#9662;</span></div>' % ctx["ONAME"] +
            '<div class="body"><div class="stage">' + ctx["LANDS"] +
            '<svg class="arcs" width="820" height="640">' + ctx["ARCS"] + '</svg>' +
            pins(ctx, box) +
            '<div class="stagebar"><span class="pill">가까운 곳</span>'
            '<span class="pill on">조금 더 멀리</span><span class="pill">아주 멀리</span></div>'
            + dock_html(kind) +
            '<div class="pop" style="left:%.1fpx;top:%.1fpx">%s</div>'
            % (o["_x"], o["_y"] - 15, detail(o)) +
            '</div><div class="panel">' + panel_filter(kind) +
            '<div class="fhead"><b>오늘의 발견</b><span>%s 출발 · %d곳</span></div>'
            % (ctx["ONAME"], len(ctx["ALL"])) +
            '<div class="sortbar"><span class="spill on">가성비순</span>'
            '<span class="spill">임박순</span><span class="spill">할인율순</span></div>'
            '<div class="feed">' + hero_card(ctx["HERO"]) +
            "".join(small_card(d, on=(d is o)) for d in ctx["FEED"]) +
            '</div><div class="cut"></div></div></div></div>')
