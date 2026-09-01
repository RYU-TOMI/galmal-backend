# -*- coding: utf-8 -*-
"""필터 도크 후보 — "지도를 얼마나 가리나".

가려지는 넓이가 아니라 **가려지는 핀 개수**로 잰다. 지도는 핀을 보여주려고 있다.
실제 deals.json 좌표로 그린다.
소유: 기획 세션. 산출물 design/dock.html
"""
import json, io, os, sys

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
from _fmt import tier, direct, card_tags, money, daterange, datesub, DATE_CSS, TOP

D = json.load(io.open(os.path.join(BASE, "..", "docs", "data", "deals.json"), encoding="utf-8"))

ALL = sorted([x for x in D["deals"] if x["o"] == "SEL"], key=lambda x: x["price"])
SEOUL = D["origins"]["SEL"]
STAGE = [d for d in ALL if d["haul"] in ("short", "medium")]

SW, SH = 540, 400
lons = [d["lon"] for d in STAGE] + [SEOUL["lon"]]
lats = [d["lat"] for d in STAGE] + [SEOUL["lat"]]
lon0, lat0 = (min(lons) + max(lons)) / 2.0, (min(lats) + max(lats)) / 2.0
pad = 52
K = min((SW - pad * 2) / max(1e-6, max(lons) - min(lons)),
        (SH - pad * 2) / max(1e-6, max(lats) - min(lats)))


def proj(lon, lat):
    return (SW / 2.0 + (lon - lon0) * K, SH / 2.0 - (lat - lat0) * K)


OX, OY = proj(SEOUL["lon"], SEOUL["lat"])
PTS = [(d, proj(d["lon"], d["lat"])) for d in STAGE]

# ── 각 후보가 무대에서 차지하는 사각형 (left, top, right, bottom) ──
BOXES = {
    "F0": (10, SH - 96, SW - 10, SH - 8),      # 하단 전폭 판
    "F1": (SW - 214, 8, SW - 8, 40),           # 우상단 알약 3개
    "F2": None,                                # 지도에 없음
    "F3": (8, 46, 104, SH - 46),               # 좌측 세로 레일
}


def covered(box):
    if not box:
        return 0
    l, t, r, b = box
    return sum(1 for _, (x, y) in PTS if l <= x <= r and t <= y <= b)


CSS = """
:root{--ink:#17201F;--sub:#6C7B78;--line:#E3EAE8;--soft:#F2F6F5;
 --accent:#F2603F;--coast:#2E7D74;--sea:#EAF1F0;--land:#DCE6E3}
*{box-sizing:border-box}
body{margin:0;font:14px/1.6 -apple-system,"Segoe UI",Roboto,"Malgun Gothic",sans-serif;
 color:var(--ink);background:#E4EDEB}
.wrap{max-width:1240px;margin:0 auto;padding:44px 26px 90px}
h1{font-size:1.9rem;letter-spacing:-.03em;margin:0 0 6px}
h1 em{font-style:normal;color:var(--accent)}
.lede{color:var(--sub);margin:0 0 30px;max-width:840px;line-height:1.75}
h2{font-size:1.12rem;margin:54px 0 10px;display:flex;align-items:center;gap:10px}
h2 .n{font-size:.68rem;background:var(--ink);color:#fff;border-radius:5px;padding:2px 7px;font-weight:800}
.note{color:var(--sub);font-size:.88rem;line-height:1.75;margin:0 0 18px;max-width:900px}
.cols{display:flex;gap:22px;flex-wrap:wrap}
.col{width:540px}
.chead{display:flex;align-items:baseline;gap:8px;margin-bottom:3px}
.cid{font-size:.66rem;font-weight:900;background:var(--ink);color:#fff;border-radius:4px;padding:2px 7px}
.cnm{font-weight:800;font-size:.95rem}
.rec{font-size:.56rem;font-weight:900;background:var(--accent);color:#fff;border-radius:4px;padding:2px 6px;vertical-align:2px}
.no{font-size:.56rem;font-weight:900;background:var(--sub);color:#fff;border-radius:4px;padding:2px 6px;vertical-align:2px}
.cdesc{color:var(--sub);font-size:.79rem;line-height:1.62;min-height:62px;margin:5px 0 9px}
.mt{display:inline-flex;align-items:baseline;gap:6px;background:#fff;border:1px solid var(--line);
 border-radius:8px;padding:5px 11px;margin-bottom:9px;font-size:.68rem;font-weight:700;color:var(--sub)}
.mt b{font-size:1.06rem;letter-spacing:-.03em;font-variant-numeric:tabular-nums;color:var(--ink)}
.mt.bad b{color:var(--accent)}
.mt.good b{color:#1E7A50}
/* 무대 */
.stage{width:540px;height:400px;position:relative;background:var(--sea);
 border:1px solid #cfdad7;border-radius:13px;overflow:hidden}
.land{position:absolute;background:var(--land);border-radius:44% 56% 38% 62%/52% 42% 58% 48%}
.pin{position:absolute;width:9px;height:9px;margin:-4.5px 0 0 -4.5px;border-radius:99px;
 background:var(--accent);box-shadow:0 0 0 3px rgba(242,96,63,.18);z-index:2}
.pin.hid{background:#B9A9A4;box-shadow:0 0 0 3px rgba(120,100,95,.16)}
.pin.orig{background:var(--coast);box-shadow:0 0 0 4px rgba(46,125,116,.2);width:11px;height:11px;margin:-5.5px 0 0 -5.5px}
.plab{position:absolute;transform:translate(-50%,-215%);font-size:.56rem;font-weight:800;
 background:#fff;border-radius:4px;padding:1px 6px;white-space:nowrap;box-shadow:0 2px 6px #0002;z-index:3}
svg.arcs{position:absolute;inset:0;pointer-events:none;z-index:1}
.stagebar{position:absolute;left:12px;top:10px;display:flex;gap:5px;z-index:7}
.pill{background:#fff;border:1px solid var(--line);border-radius:99px;padding:5px 11px;
 font-size:.66rem;font-weight:800;color:var(--sub);box-shadow:0 2px 8px #0000000f}
.pill.on{background:var(--ink);color:#fff;border-color:var(--ink)}
/* 후보별 도크 */
.dockF0{position:absolute;left:10px;right:10px;bottom:8px;height:88px;background:#fffffff2;
 border:1px solid var(--line);border-radius:12px;padding:7px 11px;z-index:8;
 box-shadow:0 6px 20px rgba(20,50,45,.1)}
.fdrow{display:flex;align-items:center;gap:8px;margin:3px 0}
.fdlabel{font-size:.62rem;font-weight:800;color:var(--sub);width:32px;flex:none}
.chips{display:flex;gap:4px;flex-wrap:wrap}
.fchip{background:var(--soft);border:1px solid var(--line);border-radius:99px;
 padding:2px 8px;font-size:.62rem;font-weight:800;color:var(--sub)}
.fchip.on{background:var(--ink);color:#fff;border-color:var(--ink)}
.brange{flex:1;height:4px;border-radius:99px;background:var(--line);position:relative}
.brange i{position:absolute;left:0;top:0;bottom:0;width:74%;border-radius:99px;background:var(--accent)}
/* F1 우상단 알약 */
.f1bar{position:absolute;right:8px;top:8px;display:flex;gap:5px;z-index:8}
.fbtn{background:#fff;border:1px solid var(--line);border-radius:99px;padding:5px 11px;
 font-size:.66rem;font-weight:800;color:var(--sub);box-shadow:0 2px 8px #0000000f;white-space:nowrap}
.fbtn.act{background:var(--accent);color:#fff;border-color:var(--accent)}
.fbtn .x{opacity:.7;margin-left:3px}
.pop1{position:absolute;right:8px;top:44px;width:236px;background:#fff;border:1px solid var(--line);
 border-radius:12px;padding:10px 11px;box-shadow:0 12px 30px rgba(16,44,38,.22);z-index:9}
.pop1 .t{font-size:.6rem;font-weight:800;color:var(--sub);margin-bottom:6px}
/* F3 좌측 레일 */
.rail{position:absolute;left:8px;top:46px;bottom:46px;width:96px;background:#fffffff2;
 border:1px solid var(--line);border-radius:12px;padding:9px 8px;z-index:8;
 box-shadow:0 6px 20px rgba(20,50,45,.1)}
.rail .t{font-size:.58rem;font-weight:800;color:var(--sub);margin:6px 0 4px}
.rail .fchip{display:block;text-align:center;margin:3px 0}
/* F2 패널 */
.panelmini{width:540px;background:var(--sea);border:1px solid #cfdad7;border-radius:13px;
 margin-top:10px;padding:10px}
.pfilter{background:#fff;border:1px solid var(--line);border-radius:11px;padding:9px 11px}
.pfhead{display:flex;justify-content:space-between;align-items:center;font-size:.72rem;font-weight:800}
.pfhead span{font-size:.62rem;color:var(--sub);font-weight:700}
table{width:100%;border-collapse:collapse;font-size:.87rem;background:#fff;
 border:1px solid var(--line);border-radius:12px;overflow:hidden}
th{text-align:left;font-weight:700;font-size:.74rem;color:var(--sub);padding:11px 12px;
 border-bottom:1px solid var(--line);background:var(--soft)}
td{padding:11px 12px;border-bottom:1px solid var(--line);vertical-align:top}
tr:last-child td{border-bottom:0}
td.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.win{color:var(--accent);font-weight:900}
.callout{background:#fff;border:1px solid var(--line);border-left:3px solid var(--accent);
 border-radius:10px;padding:16px 18px;margin:18px 0;font-size:.92rem;line-height:1.8;max-width:900px}
.callout b{color:var(--accent)}
ul.k{margin:12px 0 0;padding-left:19px;color:var(--sub);font-size:.89rem;max-width:900px}
ul.k li{margin:8px 0}ul.k b{color:var(--ink)}
code{font-family:ui-monospace,Consolas,monospace;font-size:.85em;background:var(--soft);padding:1px 5px;border-radius:4px}
.foot{margin-top:60px;padding-top:18px;border-top:1px solid var(--line);font-size:.8rem;color:var(--sub)}
""" + DATE_CSS

lands = ""
for lx, ly, lw, lh in [(40, 60, 200, 170), (200, 30, 170, 130), (110, 220, 200, 160),
                       (310, 160, 160, 140), (370, 280, 140, 110)]:
    lands += '<div class="land" style="left:%dpx;top:%dpx;width:%dpx;height:%dpx"></div>' % (lx, ly, lw, lh)

arcs = ""
for d, (x, y) in PTS:
    mx, my = (OX + x) / 2.0, (OY + y) / 2.0 - abs(x - OX) * 0.17 - 12
    arcs += ('<path d="M%.1f,%.1f Q%.1f,%.1f %.1f,%.1f" fill="none" stroke="#F2603F" '
             'stroke-width="1" opacity=".15"/>' % (OX, OY, mx, my, x, y))


def pins_for(box):
    l, t, r, b = box if box else (-1, -1, -1, -1)
    out = '<span class="pin orig" style="left:%.1fpx;top:%.1fpx"></span>' % (OX, OY)
    for d, (x, y) in PTS:
        hid = box and (l <= x <= r and t <= y <= b)
        out += ('<span class="pin%s" style="left:%.1fpx;top:%.1fpx"></span>'
                % (" hid" if hid else "", x, y))
    for d, (x, y) in PTS:
        if d.get("tier") == "major" and not (box and l <= x <= r and t <= y <= b):
            out += '<span class="plab" style="left:%.1fpx;top:%.1fpx">%s</span>' % (x, y, d["ko"])
    return out


STAGEBAR = ('<div class="stagebar"><span class="pill">가까운 곳</span>'
            '<span class="pill on">조금 더 멀리</span><span class="pill">아주 멀리</span></div>')

CHIPS_MOOD = ("".join('<span class="fchip%s">%s</span>' % (" on" if t == "문화" else "", t)
                      for t in TOP))
CHIPS_DATE = ("".join('<span class="fchip%s">%s</span>' % (" on" if t == "아무때" else "", t)
                      for t in ["아무때", "이번 주", "이번 주말", "다음 달", "날짜 지정"]))

F0 = ('<div class="dockF0">'
      '<div class="fdrow"><span class="fdlabel">날짜</span><div class="chips">' + CHIPS_DATE + '</div></div>'
      '<div class="fdrow"><span class="fdlabel">분위기</span><div class="chips">' + CHIPS_MOOD + '</div></div>'
      '<div class="fdrow"><span class="fdlabel">예산</span><span class="brange"><i></i></span>'
      '<span style="font-size:.62rem;font-weight:800">74만</span></div></div>')

F1 = ('<div class="f1bar">'
      '<span class="fbtn">날짜 &#9662;</span>'
      '<span class="fbtn act">문화<span class="x">&times;</span></span>'
      '<span class="fbtn">예산 &#9662;</span></div>'
      '<div class="pop1"><div class="t">분위기</div><div class="chips">' + CHIPS_MOOD + '</div></div>')

F3 = ('<div class="rail">'
      '<div class="t">날짜</div><span class="fchip on">아무때</span>'
      '<span class="fchip">이번 주</span><span class="fchip">주말</span>'
      '<div class="t">분위기</div>'
      + "".join('<span class="fchip%s">%s</span>' % (" on" if t == "문화" else "", t) for t in TOP[:4])
      + '</div>')

OPTS = [
    ("F0", "하단 전폭 판", "현행", "no", F0, "F0",
     "지도 아래를 <b>가로로 통째</b>로 덮는다. 세 줄을 늘 펼쳐 두므로 "
     "쓰지 않을 때도 자리를 차지한다. 라벨 칸(<code>날짜·분위기·예산</code>)이 가로를 또 먹는다."),
    ("F1", "우상단 알약 + 팝오버", "추천", "rec", F1, "F1",
     "필요할 때만 펼친다. 평소엔 <b>알약 세 개</b>뿐이고, 고른 값이 알약에 그대로 남는다"
     "(<code>문화 &times;</code>). 좌상단 단계바와 <b>대칭</b>이 된다 &mdash; "
     "왼쪽은 &lsquo;어디까지&rsquo;, 오른쪽은 &lsquo;무엇을&rsquo;."),
    ("F2", "패널 상단으로", "", "", "", "F2",
     "지도에서 <b>완전히 치운다.</b> &lsquo;지도는 무대, 패널은 도구&rsquo; 원칙엔 가장 맞다.<br>"
     "대신 <b>패널 밀도를 깎는다</b> &mdash; 방금 태그를 들어내 +27%를 벌었는데 그걸 도로 쓴다."),
    ("F3", "좌측 세로 레일", "", "", F3, "F3",
     "늘 보이고 누르기 쉽다. 다만 <b>세로로 길게</b> 가려서 "
     "지도의 왼쪽(=우리 기준 서쪽·동남아 방향)이 통째로 막힌다."),
]

cols = []
for oid, name, badge, cls, dock, key, desc in OPTS:
    box = BOXES[key]
    n = covered(box)
    b = ('<span class="rec">추천</span>' if cls == "rec"
         else '<span class="no">현행</span>' if cls == "no" else "")
    mcls = "good" if n == 0 else ("bad" if n >= 4 else "")
    if key == "F2":
        stage = ('<div class="stage">' + lands +
                 '<svg class="arcs" width="540" height="400">' + arcs + '</svg>' +
                 pins_for(None) + STAGEBAR + '</div>'
                 '<div class="panelmini"><div class="pfilter">'
                 '<div class="pfhead"><span>필터</span><span>문화 · 74만 이하</span></div>'
                 '<div class="chips" style="margin-top:7px">' + CHIPS_MOOD + '</div>'
                 '<div class="chips" style="margin-top:5px">' + CHIPS_DATE + '</div>'
                 '</div><div style="font-size:.62rem;color:var(--sub);font-weight:700;'
                 'text-align:center;padding:7px 0">&darr; 카드가 이만큼 밀린다</div></div>')
    else:
        stage = ('<div class="stage">' + lands +
                 '<svg class="arcs" width="540" height="400">' + arcs + '</svg>' +
                 pins_for(box) + STAGEBAR + dock + '</div>')
    cols.append('<div class="col"><div class="chead"><span class="cid">%s</span>'
                '<span class="cnm">%s</span>%s</div><div class="cdesc">%s</div>'
                '<div class="mt %s"><b>%d</b>곳 가림 <span style="opacity:.5">/ %d곳</span></div>'
                '%s</div>' % (oid, name, b, desc, mcls, n, len(PTS), stage))

trs = ""
for oid, name, _, cls, _, key, _ in OPTS:
    n = covered(BOXES[key])
    w = "win" if cls == "rec" else ""
    trs += ('<tr><td><b>%s</b> &nbsp;%s</td><td class="num %s">%d곳</td>'
            '<td class="num">%s</td><td>%s</td></tr>'
            % (oid, name, w, n,
               "0%" if not BOXES[key] else "%.0f%%" % (100.0 * n / len(PTS)),
               {"F0": "늘 펼쳐져 있다", "F1": "쓸 때만 펼친다",
                "F2": "지도엔 없다 · <b>패널이 좁아진다</b>",
                "F3": "늘 펼쳐져 있다"}[key]))

html = (
    "<!doctype html><html lang=ko><head><meta charset=utf-8>"
    "<meta name=viewport content='width=device-width,initial-scale=1'>"
    "<title>갈래말래 — 필터 도크</title><style>" + CSS + "</style></head><body><div class=wrap>"
    "<h1>필터 도크 &mdash; <em>어디에 둘까</em></h1>"
    "<p class=lede>가려지는 <b>넓이</b>가 아니라 <b>핀 개수</b>로 쟀다 &mdash; 지도는 핀을 보여주려고 있다. "
    "서울 출발 &lsquo;조금 더 멀리&rsquo; 단계 " + str(len(PTS)) + "곳을 실제 좌표로 그렸고, "
    "<b>가려지는 핀은 회색</b>으로 뒀다.</p>"
    "<div class=cols>" + "".join(cols) + "</div>"
    "<h2><span class=n>01</span>숫자</h2>"
    "<table><tr><th>안</th><th style='text-align:right'>가려지는 핀</th>"
    "<th style='text-align:right'>비율</th><th>메모</th></tr>" + trs + "</table>"
    "<h2><span class=n>02</span>F1을 추천한다</h2>"
    "<div class=callout>현행(F0)이 별로인 이유는 <b>모양이 아니라 크기</b>다. "
    "세 줄을 늘 펼쳐 두느라 지도 아래를 통째로 덮고, 거기에 핀이 <b>" + str(covered(BOXES["F0"])) + "곳</b> 깔려 있다.<br>"
    "필터는 <b>가끔 쓰는 도구</b>다. 늘 펼쳐 둘 이유가 없다.</div>"
    "<ul class=k>"
    "<li><b>좌상단 단계바와 대칭이 된다.</b> 왼쪽은 &lsquo;어디까지 볼까&rsquo;, "
    "오른쪽은 &lsquo;무엇을 볼까&rsquo; &mdash; 둘 다 지도를 다루는 손잡이라 같은 높이에 있는 게 맞다.</li>"
    "<li><b>고른 값이 알약에 남는다.</b> <code>문화 &times;</code>처럼 보이므로 "
    "펼치지 않아도 <b>지금 뭘 걸었는지</b> 안다. F0은 칩이 눌린 걸 보려면 도크를 봐야 한다.</li>"
    "<li><b>패널 밀도를 안 깎는다.</b> F2는 원칙엔 맞지만 카드를 밀어낸다 &mdash; "
    "태그를 들어내 얻은 <b>+27%</b>를 도로 쓰는 셈이다.</li>"
    "<li><b>모바일에서도 같은 모양이 된다.</b> 알약 세 개는 좁은 폭에서도 한 줄에 들어가고, "
    "팝오버는 그대로 <b>하단 시트</b>가 되면 된다 &mdash; 상세와 같은 패턴이라 새로 배울 게 없다.</li>"
    "</ul>"
    "<p class=note>&#9888; <b>펼쳤을 때는 F1도 가린다.</b> 위 그림은 <code>분위기</code>를 펼친 상태이고, "
    "그때 팝오버가 오른쪽 위를 덮는다. 다만 <b>쓰는 순간에만</b>이고, "
    "닫으면 다시 " + str(covered(BOXES["F1"])) + "곳으로 돌아온다.</p>"
    "<p class=foot>생성 <b>design/build_dock.py</b> &middot; 데이터 <b>docs/data/deals.json</b> &middot; "
    "확정 홈 <b>home.html</b> &middot; 스펙 <b>../SPEC.md</b></p>"
    "</div></body></html>")

out = os.path.join(BASE, "dock.html")
io.open(out, "w", encoding="utf-8").write(html)
print("dock.html  %.1fKB" % (len(html) / 1024.0))
for oid, name, _, _, _, key, _ in OPTS:
    print("  %s %-16s 가려지는 핀 %2d / %d곳" % (oid, name, covered(BOXES[key]), len(PTS)))
