# -*- coding: utf-8 -*-
"""발견 홈 셸 렌더러 — 도크만 갈아끼울 수 있게 함수로 뺐다.

home.html(확정 정리)과 dock.html(도크 4안 비교)이 같은 함수를 쓴다.
같은 화면을 두 번 그리면 하나는 틀어진다.
소유: 기획 세션.
"""
import os, sys

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
from _fmt import (tier, direct, card_tags, money, daterange, datesub,
                  DATE_CSS, TOP)

SW, SH = 820, 640          # 지도 무대
PANEL_W = 380

# ── 각 도크가 무대에서 차지하는 사각형 (left, top, right, bottom) ──
BOXES = {
    "F0": (16, SH - 104, SW - 16, SH - 14),
    "F1": (SW - 236, 12, SW - 12, 46),
    "F2": None,
    "F3": (12, 54, 116, SH - 54),
}

DOCK_NAME = {
    "F0": "하단 전폭 판",
    "F1": "우상단 알약 + 팝오버",
    "F2": "패널 상단으로",
    "F3": "좌측 세로 레일",
}

CSS = """
:root{--ink:#17201F;--sub:#6C7B78;--line:#E3EAE8;--soft:#F2F6F5;
 --accent:#F2603F;--coast:#2E7D74;--sea:#EAF1F0;--land:#DCE6E3;--card:#fff}
*{box-sizing:border-box}
body{margin:0;font:14px/1.6 -apple-system,"Segoe UI",Roboto,"Malgun Gothic",sans-serif;
 color:var(--ink);background:#E4EDEB}
.wrap{max-width:1320px;margin:0 auto;padding:44px 26px 90px}
h1{font-size:1.9rem;letter-spacing:-.03em;margin:0 0 6px}
h1 em{font-style:normal;color:var(--accent)}
.lede{color:var(--sub);margin:0 0 26px;max-width:860px;line-height:1.75}
h2{font-size:1.12rem;margin:56px 0 10px;display:flex;align-items:center;gap:10px}
h2 .n{font-size:.68rem;background:var(--ink);color:#fff;border-radius:5px;padding:2px 7px;font-weight:800}
.note{color:var(--sub);font-size:.88rem;line-height:1.75;margin:0 0 18px;max-width:900px}
.app{width:1200px;border:1px solid #cfdad7;border-radius:16px;overflow:hidden;
 background:var(--card);box-shadow:0 14px 40px rgba(20,50,45,.14);position:relative}
.hdr{display:flex;align-items:center;gap:20px;height:56px;padding:0 18px;
 background:var(--card);border-bottom:1px solid var(--line)}
.logo{font-weight:900;font-size:1.02rem;letter-spacing:-.03em}
.logo i{font-style:normal;color:var(--accent)}
.nav{display:flex;gap:15px;font-size:.82rem;font-weight:800}
.nav .a{color:var(--ink);border-bottom:2px solid var(--accent);padding-bottom:2px}
.nav .m{color:var(--sub)}
.origin{margin-left:auto;background:var(--soft);border:1px solid var(--line);border-radius:99px;
 padding:5px 13px;font-size:.8rem;font-weight:800}
.body{display:flex;height:640px}
.stage{width:820px;flex:none;position:relative;background:var(--sea);overflow:hidden}
.land{position:absolute;background:var(--land);border-radius:44% 56% 38% 62%/52% 42% 58% 48%}
svg.arcs{position:absolute;inset:0;pointer-events:none;z-index:1}
.pin{position:absolute;width:11px;height:11px;margin:-5.5px 0 0 -5.5px;border-radius:99px;
 background:var(--accent);box-shadow:0 0 0 3px rgba(242,96,63,.18);z-index:2}
.pin.on{width:19px;height:19px;margin:-9.5px 0 0 -9.5px;box-shadow:0 0 0 7px rgba(242,96,63,.28);z-index:4}
.pin.hid{background:#B9A9A4;box-shadow:0 0 0 3px rgba(120,100,95,.14)}
.pin.orig{background:var(--coast);box-shadow:0 0 0 4px rgba(46,125,116,.2);
 width:13px;height:13px;margin:-6.5px 0 0 -6.5px}
.plab{position:absolute;transform:translate(-50%,-210%);font-size:.62rem;font-weight:800;
 background:#fff;border-radius:5px;padding:2px 7px;white-space:nowrap;box-shadow:0 2px 7px #0002;z-index:3}
.plab.orig{background:var(--coast);color:#fff}
.stagebar{position:absolute;left:16px;top:14px;display:flex;gap:6px;z-index:7}
.pill{background:#fff;border:1px solid var(--line);border-radius:99px;padding:6px 13px;
 font-size:.74rem;font-weight:800;color:var(--sub);box-shadow:0 2px 8px #0000000f}
.pill.on{background:var(--ink);color:#fff;border-color:var(--ink)}
/* 도크 공통 */
.chips{display:flex;gap:5px;flex-wrap:wrap}
.fchip{background:var(--soft);border:1px solid var(--line);border-radius:99px;
 padding:3px 10px;font-size:.68rem;font-weight:800;color:var(--sub)}
.fchip.on{background:var(--ink);color:#fff;border-color:var(--ink)}
.fchip.new{border-color:var(--accent);color:var(--accent);background:#FFF4F1}
.brange{flex:1;height:4px;border-radius:99px;background:var(--line);position:relative}
.brange i{position:absolute;left:0;top:0;bottom:0;width:74%;border-radius:99px;background:var(--accent)}
/* F0 */
.dock0{position:absolute;left:16px;right:16px;bottom:14px;background:#fffffff2;
 border:1px solid var(--line);border-radius:13px;padding:9px 13px;z-index:8;
 box-shadow:0 6px 20px rgba(20,50,45,.1)}
.fdrow{display:flex;align-items:center;gap:9px;margin:4px 0}
.fdlabel{font-size:.66rem;font-weight:800;color:var(--sub);width:36px;flex:none}
.bval{font-size:.66rem;font-weight:800}
/* F1 */
.f1bar{position:absolute;right:12px;top:12px;display:flex;gap:6px;z-index:8}
.fbtn{background:#fff;border:1px solid var(--line);border-radius:99px;padding:6px 13px;
 font-size:.72rem;font-weight:800;color:var(--sub);box-shadow:0 2px 8px #0000000f;white-space:nowrap}
.fbtn.act{background:var(--accent);color:#fff;border-color:var(--accent)}
.fbtn .x{opacity:.7;margin-left:4px}
.pop1{position:absolute;right:12px;top:50px;width:262px;background:#fff;border:1px solid var(--line);
 border-radius:13px;padding:11px 12px;box-shadow:0 14px 34px rgba(16,44,38,.24);z-index:9}
.pop1 .t{font-size:.62rem;font-weight:800;color:var(--sub);margin-bottom:7px}
/* F3 */
.rail{position:absolute;left:12px;top:54px;bottom:54px;width:104px;background:#fffffff2;
 border:1px solid var(--line);border-radius:13px;padding:10px 9px;z-index:8;
 box-shadow:0 6px 20px rgba(20,50,45,.1);overflow:hidden}
.rail .t{font-size:.6rem;font-weight:800;color:var(--sub);margin:7px 0 4px}
.rail .fchip{display:block;text-align:center;margin:3px 0;padding:3px 4px}
/* 상세 */
.pop{position:absolute;width:224px;z-index:10;transform:translate(-50%,-100%)}
.pop:after{content:"";position:absolute;left:50%;bottom:-8px;margin-left:-8px;
 border:8px solid transparent;border-top-color:#fff}
.det{background:#fff;border-radius:13px;overflow:hidden;box-shadow:0 16px 40px rgba(16,44,38,.3)}
.det .ph{height:94px;position:relative;background:linear-gradient(140deg,#b9d1cc,#dce8e5)}
.phtags{position:absolute;left:7px;right:7px;bottom:7px;display:flex;gap:3px;flex-wrap:wrap}
.phtag{font-size:.52rem;font-weight:800;color:#fff;background:rgba(6,20,18,.52);
 border-radius:4px;padding:1px 6px;white-space:nowrap}
.cityover{position:absolute;left:9px;bottom:24px;color:#fff;font-weight:900;font-size:.98rem;
 text-shadow:0 1px 7px #0009;letter-spacing:-.02em}
.closex{position:absolute;right:7px;top:7px;width:20px;height:20px;border-radius:99px;
 background:rgba(6,20,18,.45);color:#fff;font-size:.66rem;font-weight:900;
 display:flex;align-items:center;justify-content:center}
.db{padding:10px}
.dsec{font-size:.55rem;font-weight:800;color:var(--sub);margin:9px 0 5px;padding-top:8px;
 border-top:1px dashed var(--line)}
.cmp{display:flex;align-items:center;gap:6px;font-size:.57rem;margin:3px 0}
.cmp .bar{flex:1;height:6px;border-radius:99px;background:var(--soft);overflow:hidden}
.cmp .bar i{display:block;height:100%;border-radius:99px;background:var(--accent)}
.cmp .bar.mut i{background:#c3cfcc}
.cmp b{font-variant-numeric:tabular-nums;white-space:nowrap;font-size:.59rem}
.rec2{font-size:.58rem;font-weight:800;color:var(--accent);margin-top:5px}
.lnk{display:flex;justify-content:space-between;background:var(--soft);border-radius:7px;
 padding:5px 8px;font-size:.58rem;font-weight:800;margin-top:4px}
.lnk .p{font-variant-numeric:tabular-nums}
.go{margin-top:8px;background:var(--accent);color:#fff;text-align:center;font-weight:800;
 font-size:.66rem;border-radius:8px;padding:8px 0}
.ad{font-size:.48rem;color:var(--sub);line-height:1.5;margin-top:6px;text-align:center}
/* 패널 */
.panel{width:380px;flex:none;background:var(--sea);border-left:1px solid var(--line);
 padding:0 10px;position:relative;overflow:hidden}
.pfilter{background:#fff;border:1px solid var(--line);border-radius:12px;padding:10px 11px;margin-top:10px}
.pfhead{display:flex;justify-content:space-between;align-items:center;font-size:.76rem;font-weight:800}
.pfhead span{font-size:.64rem;color:var(--sub);font-weight:700}
.fhead{padding:12px 2px 8px;display:flex;align-items:baseline;justify-content:space-between}
.fhead b{font-size:.98rem;letter-spacing:-.02em}
.fhead span{font-size:.66rem;color:var(--sub);font-weight:700}
.sortbar{display:flex;gap:5px;padding-bottom:9px}
.spill{background:#fff;border:1px solid var(--line);border-radius:99px;padding:4px 11px;
 font-size:.66rem;font-weight:800;color:var(--sub)}
.spill.on{background:var(--ink);color:#fff;border-color:var(--ink)}
.feed{display:flex;flex-direction:column;gap:9px}
.fcard{display:flex;gap:11px;background:#fff;border:1.5px solid var(--line);
 border-radius:13px;padding:10px;overflow:hidden}
.fcard.on{border-color:var(--accent);box-shadow:0 5px 16px rgba(242,96,63,.2)}
.thumb{flex:none;width:62px;height:62px;border-radius:10px;
 background:linear-gradient(140deg,#cfe0dc,#e9efed)}
.fbody{flex:1;min-width:0}
.frow{display:flex;justify-content:space-between;align-items:center;gap:6px}
.fcity{font-size:.98rem;font-weight:900;letter-spacing:-.02em;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.prow{display:flex;justify-content:space-between;align-items:center;gap:8px;margin-top:2px}
.price{font-weight:900;font-size:1.18rem;letter-spacing:-.03em;font-variant-numeric:tabular-nums}
.price small{font-size:.6em;font-weight:700;color:var(--sub);margin-left:2px}
.dmain{font-size:.76rem;margin-top:5px}
.dsub{font-size:.64rem;margin-top:2px}
.bdg{font-size:.6rem;font-weight:800;border-radius:99px;padding:2px 9px;flex:none;
 background:var(--coast);color:#fff;white-space:nowrap}
.stamp{flex:none;font-weight:900;white-space:nowrap;border-radius:4px}
.stamp.t1{transform:rotate(-7deg);border:1.5px solid var(--accent);color:var(--accent);
 font-size:.54rem;padding:1px 5px;background:#fff}
.stamp.t2{transform:rotate(-8deg);background:var(--accent);color:#fff;font-size:.6rem;padding:2px 7px;
 box-shadow:0 2px 6px rgba(242,96,63,.34)}
.stamp.t3{transform:rotate(-9deg) scale(1.04);background:linear-gradient(135deg,#F2603F,#FF8A63 42%,#C6472A);
 color:#fff;font-size:.64rem;padding:2px 8px;
 box-shadow:0 0 0 2px #fff,0 0 0 5px rgba(242,96,63,.2),0 4px 12px rgba(198,71,42,.34)}
/* 신기록 — 도장과 형태를 가른다: 기울기·테두리 없음 */
.rec{flex:none;font-size:.6rem;font-weight:900;color:var(--accent);white-space:nowrap}
.hero{flex-direction:column;gap:0;padding:0}
.hero .ph{width:100%;height:104px;position:relative;background:linear-gradient(140deg,#c6dbd6,#e4edea)}
.hero .hb{padding:10px}
.pick{position:absolute;left:9px;top:9px;background:#fff;color:var(--accent);font-weight:900;
 font-size:.6rem;padding:2px 8px;border-radius:99px;box-shadow:0 2px 6px #0002}
.cut{position:absolute;left:0;right:0;bottom:0;height:74px;pointer-events:none;
 background:linear-gradient(transparent,var(--sea) 66%)}
.b{position:absolute;width:21px;height:21px;border-radius:99px;background:var(--ink);color:#fff;
 font-size:.64rem;font-weight:900;display:flex;align-items:center;justify-content:center;
 box-shadow:0 2px 8px #0004;z-index:20}
.b.q{background:#fff;color:var(--ink);border:2px solid var(--ink)}
table{width:100%;border-collapse:collapse;font-size:.87rem;background:#fff;
 border:1px solid var(--line);border-radius:12px;overflow:hidden}
th{text-align:left;font-weight:700;font-size:.74rem;color:var(--sub);padding:11px 12px;
 border-bottom:1px solid var(--line);background:var(--soft)}
td{padding:11px 12px;border-bottom:1px solid var(--line);vertical-align:top}
tr:last-child td{border-bottom:0}
td.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.win{color:var(--accent);font-weight:900}
.num2{display:inline-flex;width:20px;height:20px;border-radius:99px;background:var(--ink);color:#fff;
 font-size:.62rem;font-weight:900;align-items:center;justify-content:center;margin-right:7px}
.num2.q{background:#fff;color:var(--ink);border:2px solid var(--ink)}
.callout{background:#fff;border:1px solid var(--line);border-left:3px solid var(--accent);
 border-radius:10px;padding:16px 18px;margin:18px 0;font-size:.92rem;line-height:1.8;max-width:900px}
.callout b{color:var(--accent)}
ul.k{margin:12px 0 0;padding-left:19px;color:var(--sub);font-size:.89rem;max-width:900px}
ul.k li{margin:8px 0}ul.k b{color:var(--ink)}
code{font-family:ui-monospace,Consolas,monospace;font-size:.85em;background:var(--soft);padding:1px 5px;border-radius:4px}
.foot{margin-top:60px;padding-top:18px;border-top:1px solid var(--line);font-size:.8rem;color:var(--sub)}
""" + DATE_CSS


# ── 신기록 판정 (SPEC.md §CH3, 2026-09-01 확정) ────────────────
OBS_FLOOR = 14


def record(d):
    """`low`가 있고 `obs_days >= 14`이고 `price < low`. 타이기록은 신기록이 아니다."""
    lo = d.get("low")
    return lo is not None and d.get("obs_days", 0) >= OBS_FLOOR and d["price"] < lo


def claim(d):
    """카드는 '왜 싼가'를 한 번만 말한다 — 도장 우선, 없으면 신기록."""
    t = tier(d)
    if t:
        return '<span class="stamp %s">%d%%&darr;</span>' % (t, d["discount"])
    if record(d):
        return '<span class="rec">%d일 최저</span>' % d.get("obs_days", 0)
    return ""


CHIPS_MOOD = "".join('<span class="fchip%s">%s</span>' % (" new" if t == "문화" else "", t)
                     for t in TOP)
CHIPS_DATE = "".join('<span class="fchip%s">%s</span>' % (" on" if t == "아무때" else "", t)
                     for t in ["아무때", "이번 주", "이번 주말", "다음 달", "날짜 지정"])


def dock_html(kind):
    if kind == "F0":
        return ('<div class="dock0">'
                '<div class="fdrow"><span class="fdlabel">날짜</span>'
                '<div class="chips">' + CHIPS_DATE + '</div></div>'
                '<div class="fdrow"><span class="fdlabel">분위기</span>'
                '<div class="chips">' + CHIPS_MOOD + '</div></div>'
                '<div class="fdrow"><span class="fdlabel">예산</span>'
                '<span class="brange"><i></i></span><span class="bval">74만 이하</span></div></div>')
    if kind == "F1":
        return ('<div class="f1bar">'
                '<span class="fbtn">날짜 &#9662;</span>'
                '<span class="fbtn act">문화<span class="x">&times;</span></span>'
                '<span class="fbtn">예산 &#9662;</span></div>'
                '<div class="pop1"><div class="t">분위기</div>'
                '<div class="chips">' + CHIPS_MOOD + '</div></div>')
    if kind == "F3":
        return ('<div class="rail"><div class="t">날짜</div>'
                '<span class="fchip on">아무때</span><span class="fchip">이번 주</span>'
                '<span class="fchip">주말</span><span class="fchip">다음 달</span>'
                '<div class="t">분위기</div>'
                + "".join('<span class="fchip%s">%s</span>' % (" new" if t == "문화" else "", t)
                          for t in TOP)
                + '</div>')
    return ""


def panel_filter(kind):
    if kind != "F2":
        return ""
    return ('<div class="pfilter"><div class="pfhead"><span>필터</span>'
            '<span>문화 &middot; 74만 이하</span></div>'
            '<div class="chips" style="margin-top:8px">' + CHIPS_MOOD + '</div>'
            '<div class="chips" style="margin-top:5px">' + CHIPS_DATE + '</div>'
            '<div class="fdrow" style="margin-top:7px"><span class="fdlabel">예산</span>'
            '<span class="brange"><i></i></span><span class="bval">74만</span></div></div>')
