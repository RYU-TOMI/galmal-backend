# -*- coding: utf-8 -*-
"""발견 홈 — 지금까지 확정한 것을 한 화면에 모은 목업.

빈 상자가 아니라 실제 deals.json으로 채운다. 움직임은 없다(정지 화면).
확정된 것은 번호를 달고 아래 표에서 설명한다. 아직 안 정한 것은 현행대로 두고 표시한다.
소유: 기획 세션. 산출물 design/home.html
"""
import json, io, os, math

BASE = os.path.dirname(os.path.abspath(__file__))
D = json.load(io.open(os.path.join(BASE, "..", "docs", "data", "deals.json"), encoding="utf-8"))

TOP = ["해변", "도시", "미식", "자연", "문화", "온천"]
SUB = {"리조트", "스노클링", "서핑", "섬", "야경", "쇼핑", "마천루", "골목",
       "야시장", "길거리음식", "화산", "트레킹", "사막", "폭포", "사원", "유적", "고성", "미술관"}
TIERS = [(35, "t3"), (25, "t2"), (15, "t1")]


def tier(d):
    v = d.get("discount", 0)
    for lo, t in TIERS:
        if v >= lo:
            return t
    return None


def direct(d):
    return d["transfers"] == 0 and d["haul"] != "short"


def card_tags(tags):
    s = [t for t in tags if t in SUB]
    tp = [t for t in tags if t in TOP]
    return (s + tp[:1] if s else tp[:2])[:4]


def money(v):
    return "{:,}".format(v)


ALL = sorted([x for x in D["deals"] if x["o"] == "SEL"], key=lambda x: x["price"])
SEOUL = D["origins"]["SEL"]

# ── 단계 "조금 더 멀리"(근거리 + 중거리)를 그린다 ───────────────
STAGE = [d for d in ALL if d["haul"] in ("short", "medium")]
SW, SH = 820, 640

lons = [d["lon"] for d in STAGE] + [SEOUL["lon"]]
lats = [d["lat"] for d in STAGE] + [SEOUL["lat"]]
lon0, lat0 = (min(lons) + max(lons)) / 2.0, (min(lats) + max(lats)) / 2.0
pad = 74
kx = (SW - pad * 2) / max(1e-6, (max(lons) - min(lons)))
ky = (SH - pad * 2) / max(1e-6, (max(lats) - min(lats)))
K = min(kx, ky)


def proj(lon, lat):
    return (SW / 2.0 + (lon - lon0) * K, SH / 2.0 - (lat - lat0) * K)


OX, OY = proj(SEOUL["lon"], SEOUL["lat"])
for d in STAGE:
    d["_x"], d["_y"] = proj(d["lon"], d["lat"])

HERO = ALL[0]
# 상세를 열어 둘 딜 — 무대 가운데쯤이고 도장·태그가 붙은 것
def _fits(d):
    """상세 카드가 무대 밖으로 안 넘치는 자리인가. 카드는 핀 위로 224x약250 피어난다."""
    return 130 < d["_x"] < SW - 130 and 265 < d["_y"] < SH - 30

# 도장이 붙은 딜을 우선한다 — 목업에서 3티어를 보여야 하므로.
# 조건을 단계적으로 풀어 항상 하나는 고른다.
# 히어로와 겹치면 목업이 헷갈리므로 제외한다.
POOL = [d for d in STAGE if d is not HERO]
OPEN = next((d for d in POOL if tier(d) and len(card_tags(d["tags"])) >= 3 and _fits(d)),
       next((d for d in POOL if tier(d) and _fits(d)),
       next((d for d in POOL if tier(d)),
       next((d for d in POOL if _fits(d)), POOL[len(POOL) // 2]))))
FEED = [d for d in ALL[1:9]]

# 라벨은 major만 (LOD 규칙)
LABELED = [d for d in STAGE if d.get("tier") == "major"][:7]

CSS = """
:root{--ink:#17201F;--sub:#6C7B78;--line:#E3EAE8;--soft:#F2F6F5;
 --accent:#F2603F;--coast:#2E7D74;--sea:#EAF1F0;--land:#DCE6E3;--card:#fff}
*{box-sizing:border-box}
body{margin:0;font:14px/1.6 -apple-system,"Segoe UI",Roboto,"Malgun Gothic",sans-serif;
 color:var(--ink);background:#E4EDEB}
.wrap{max-width:1320px;margin:0 auto;padding:44px 26px 90px}
h1{font-size:1.9rem;letter-spacing:-.03em;margin:0 0 6px}
h1 em{font-style:normal;color:var(--accent)}
.lede{color:var(--sub);margin:0 0 26px;max-width:840px;line-height:1.75}
h2{font-size:1.12rem;margin:56px 0 10px;display:flex;align-items:center;gap:10px}
h2 .n{font-size:.68rem;background:var(--ink);color:#fff;border-radius:5px;padding:2px 7px;font-weight:800}
.note{color:var(--sub);font-size:.88rem;line-height:1.75;margin:0 0 18px;max-width:900px}
/* ── 앱 셸 ── */
.app{width:1200px;border:1px solid #cfdad7;border-radius:16px;overflow:hidden;
 background:var(--card);box-shadow:0 14px 40px rgba(20,50,45,.14)}
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
svg.arcs{position:absolute;inset:0;pointer-events:none}
.pin{position:absolute;width:11px;height:11px;margin:-5.5px 0 0 -5.5px;border-radius:99px;
 background:var(--accent);box-shadow:0 0 0 3px rgba(242,96,63,.18)}
.pin.on{width:19px;height:19px;margin:-9.5px 0 0 -9.5px;box-shadow:0 0 0 7px rgba(242,96,63,.28);z-index:4}
.pin.orig{background:var(--coast);box-shadow:0 0 0 4px rgba(46,125,116,.2);width:13px;height:13px;margin:-6.5px 0 0 -6.5px}
.plab{position:absolute;transform:translate(-50%,-210%);font-size:.62rem;font-weight:800;
 background:#fff;border-radius:5px;padding:2px 7px;white-space:nowrap;box-shadow:0 2px 7px #0002}
.plab.orig{background:var(--coast);color:#fff}
/* 단계바 */
.stagebar{position:absolute;left:16px;top:14px;display:flex;gap:6px;z-index:6}
.pill{background:#fff;border:1px solid var(--line);border-radius:99px;padding:6px 13px;
 font-size:.74rem;font-weight:800;color:var(--sub);box-shadow:0 2px 8px #0000000f}
.pill.on{background:var(--ink);color:#fff;border-color:var(--ink)}
/* 필터 도크 */
.dock{position:absolute;left:16px;right:16px;bottom:14px;background:#fffffff2;
 border:1px solid var(--line);border-radius:13px;padding:9px 13px;
 box-shadow:0 6px 20px rgba(20,50,45,.1);z-index:6}
.fdrow{display:flex;align-items:center;gap:9px;margin:4px 0}
.fdlabel{font-size:.66rem;font-weight:800;color:var(--sub);width:36px;flex:none}
.chips{display:flex;gap:5px;flex-wrap:wrap}
.fchip{background:var(--soft);border:1px solid var(--line);border-radius:99px;
 padding:3px 10px;font-size:.68rem;font-weight:800;color:var(--sub)}
.fchip.on{background:var(--ink);color:#fff;border-color:var(--ink)}
.fchip.new{border-color:var(--accent);color:var(--accent);background:#FFF4F1}
.brange{flex:1;height:4px;border-radius:99px;background:var(--line);position:relative}
.brange i{position:absolute;left:0;top:0;bottom:0;width:74%;border-radius:99px;background:var(--accent)}
.bval{font-size:.66rem;font-weight:800}
/* 열린 상세 */
.pop{position:absolute;width:224px;z-index:8;transform:translate(-50%,-100%)}
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
.lnk{display:flex;justify-content:space-between;background:var(--soft);border-radius:7px;
 padding:5px 8px;font-size:.58rem;font-weight:800;margin-top:4px}
.lnk .p{font-variant-numeric:tabular-nums}
.go{margin-top:8px;background:var(--accent);color:#fff;text-align:center;font-weight:800;
 font-size:.66rem;border-radius:8px;padding:8px 0}
.ad{font-size:.48rem;color:var(--sub);line-height:1.5;margin-top:6px;text-align:center}
/* 패널 */
.panel{width:380px;flex:none;background:var(--sea);border-left:1px solid var(--line);
 padding:0 10px;position:relative;overflow:hidden}
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
.dmain{font-size:.72rem;font-weight:800;margin-top:5px;font-variant-numeric:tabular-nums}
.dsub{font-size:.64rem;font-weight:700;color:var(--sub);margin-top:2px;font-variant-numeric:tabular-nums}
.wk{color:var(--sub);font-weight:700}
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
.hero{flex-direction:column;gap:0;padding:0}
.hero .ph{width:100%;height:104px;position:relative;background:linear-gradient(140deg,#c6dbd6,#e4edea)}
.hero .hb{padding:10px}
.pick{position:absolute;left:9px;top:9px;background:#fff;color:var(--accent);font-weight:900;
 font-size:.6rem;padding:2px 8px;border-radius:99px;box-shadow:0 2px 6px #0002}
.cut{position:absolute;left:0;right:0;bottom:0;height:74px;pointer-events:none;
 background:linear-gradient(transparent,var(--sea) 66%)}
/* 번호 뱃지 */
.b{position:absolute;width:21px;height:21px;border-radius:99px;background:var(--ink);color:#fff;
 font-size:.64rem;font-weight:900;display:flex;align-items:center;justify-content:center;
 box-shadow:0 2px 8px #0004;z-index:20}
.b.q{background:#fff;color:var(--ink);border:2px solid var(--ink)}
/* 표 */
table{width:100%;border-collapse:collapse;font-size:.87rem;background:#fff;
 border:1px solid var(--line);border-radius:12px;overflow:hidden}
th{text-align:left;font-weight:700;font-size:.74rem;color:var(--sub);padding:11px 12px;
 border-bottom:1px solid var(--line);background:var(--soft)}
td{padding:11px 12px;border-bottom:1px solid var(--line);vertical-align:top}
tr:last-child td{border-bottom:0}
td.k{white-space:nowrap;font-weight:800}
.num{display:inline-flex;width:20px;height:20px;border-radius:99px;background:var(--ink);color:#fff;
 font-size:.62rem;font-weight:900;align-items:center;justify-content:center;margin-right:7px}
.num.q{background:#fff;color:var(--ink);border:2px solid var(--ink)}
code{font-family:ui-monospace,Consolas,monospace;font-size:.85em;background:var(--soft);padding:1px 5px;border-radius:4px}
.foot{margin-top:60px;padding-top:18px;border-top:1px solid var(--line);font-size:.8rem;color:var(--sub)}
"""


def stamp_of(d):
    t = tier(d)
    return ('<span class="stamp %s">%d%%&darr;</span>' % (t, d["discount"])) if t else ""


def small_card(d, on=False):
    """작은 카드 — 태그 없음(2026-09-01 확정)."""
    bdg = '<span class="bdg">&#9992; 직항</span>' if direct(d) else ""
    return ('<div class="fcard%s"><div class="thumb"></div><div class="fbody">'
            '<div class="frow"><span class="fcity">%s</span>%s</div>'
            '<div class="prow"><span class="price">%s<small>원</small></span>%s</div>'
            '<div class="dmain">%s</div><div class="dsub">%s &middot; %s</div>'
            '</div></div>'
            % (" on" if on else "", d["ko"], stamp_of(d), money(d["price"]), bdg,
               d["dep"], d.get("nights", ""), d["when"]))


def hero_card(d):
    tags = "".join('<span class="phtag">%s</span>' % t for t in card_tags(d["tags"]))
    bdg = '<span class="bdg">&#9992; 직항</span>' if direct(d) else ""
    return ('<div class="fcard hero"><div class="ph">'
            '<span class="pick">오늘의 발견</span>'
            '<div class="phtags">%s</div>'
            '<span class="cityover">%s</span></div>'
            '<div class="hb"><div class="prow" style="margin-top:0">'
            '<span class="price">%s<small>원</small></span>%s</div>'
            '<div class="dmain">%s</div><div class="dsub">%s &middot; %s</div>'
            '<div style="margin-top:7px">%s</div></div></div>'
            % (tags, d["ko"], money(d["price"]), stamp_of(d),
               d["dep"], d.get("nights", ""), d["when"], bdg))


def detail(d):
    tags = "".join('<span class="phtag">%s</span>' % t for t in card_tags(d["tags"]))
    bdg = '<span class="bdg">&#9992; 직항</span>' if direct(d) else ""
    med = d.get("median") or int(d["price"] * 1.25)
    ratio = int(min(1.0, d["price"] / float(med)) * 100)
    links = (d.get("links") or [])[:3]
    lnk = "".join('<div class="lnk"><span>%s</span><span class="p">%s원</span></div>'
                  % (l.get("name", "비교 사이트"), money(l.get("price", d["price"])))
                  for l in links) or \
          ('<div class="lnk"><span>비교 사이트</span><span class="p">%s원</span></div>'
           % money(d["price"]))
    return ('<div class="det"><div class="ph"><span class="closex">&times;</span>'
            '<div class="phtags">%s</div><span class="cityover">%s</span></div><div class="db">'
            '<div class="prow" style="margin-top:0">'
            '<span class="price" style="font-size:1.08rem">%s<small>원</small></span>%s</div>'
            '<div class="prow" style="margin-top:3px">'
            '<span class="dmain" style="margin-top:0">%s <span class="wk">&middot; %s</span></span>%s</div>'
            '<div class="dsec">평소 시세와 비교</div>'
            '<div class="cmp"><span style="width:36px;color:var(--sub)">평소</span>'
            '<span class="bar mut"><i style="width:100%%"></i></span><b>%s원</b></div>'
            '<div class="cmp"><span style="width:36px;font-weight:800">지금</span>'
            '<span class="bar"><i style="width:%d%%"></i></span><b>%s원</b></div>'
            '<div class="dsec">어디가 제일 싼지 비교해보세요</div>%s'
            '<div class="go">갈래 &rarr; 예약처로</div>'
            '<div class="ad">위 가격은 발견가(스캔 시점) · 실시간 최저가는 각 사이트에서 확인하세요<br>'
            '일부는 예약 시 수수료 (광고)</div></div></div>'
            % (tags, d["ko"], money(d["price"]), stamp_of(d),
               d["dep"], d.get("nights", ""), bdg, money(med), ratio, money(d["price"]), lnk))


# ── 지도 요소 ──────────────────────────────────────────────────
lands = ""
for lx, ly, lw, lh in [(70, 90, 300, 250), (300, 60, 260, 200), (180, 330, 300, 240),
                       (470, 250, 240, 210), (560, 430, 220, 170), (40, 400, 180, 160)]:
    lands += '<div class="land" style="left:%dpx;top:%dpx;width:%dpx;height:%dpx"></div>' % (lx, ly, lw, lh)

paths = ""
for d in STAGE:
    mx = (OX + d["_x"]) / 2.0
    my = (OY + d["_y"]) / 2.0 - abs(d["_x"] - OX) * 0.17 - 16
    op = ".72" if d is OPEN else ".16"
    wid = "1.7" if d is OPEN else "1"
    paths += ('<path d="M%.1f,%.1f Q%.1f,%.1f %.1f,%.1f" fill="none" stroke="#F2603F" '
              'stroke-width="%s" opacity="%s"/>' % (OX, OY, mx, my, d["_x"], d["_y"], wid, op))

pins = '<span class="pin orig" style="left:%.1fpx;top:%.1fpx"></span>' % (OX, OY)
pins += '<span class="plab orig" style="left:%.1fpx;top:%.1fpx">서울</span>' % (OX, OY)
for d in STAGE:
    pins += ('<span class="pin%s" style="left:%.1fpx;top:%.1fpx"></span>'
             % (" on" if d is OPEN else "", d["_x"], d["_y"]))
for d in LABELED:
    if d is not OPEN:
        pins += ('<span class="plab" style="left:%.1fpx;top:%.1fpx">%s</span>'
                 % (d["_x"], d["_y"], d["ko"]))
pins += '<span class="plab" style="left:%.1fpx;top:%.1fpx">%s</span>' % (OPEN["_x"], OPEN["_y"], OPEN["ko"])

badges = [
    (1, 14, 12, False),                                             # 단계바
    (2, OPEN["_x"] - 128, OPEN["_y"] - 250, False),                 # 열린 상세
    (3, OPEN["_x"] + 14, OPEN["_y"] - 8, False),                    # 핀 강조
    (4, 838, 46, False),                                            # 히어로 사진 태그
    (5, 838, 236, False),                                           # 작은 카드 태그 없음
    (6, 1152, 236, False),                                          # 도장
    (7, 1152, 300, False),                                          # 직항 배지
    (8, 838, 300, False),                                           # 날짜 두 단
    (9, 14, 470, True),                                             # 필터 칩(문화)
    (10, 14, 556, True),                                            # 도크 위치 미정
]
bhtml = "".join('<span class="b%s" style="left:%dpx;top:%dpx">%d</span>'
                % (" q" if q else "", x, y, n) for n, x, y, q in badges)

app = (
    '<div class="app" style="position:relative">' + bhtml +
    '<div class="hdr"><span class="logo">갈래<i>말래</i></span>'
    '<span class="nav"><span class="a">발견</span><span class="m">노선별</span></span>'
    '<span class="origin">서울 출발 &#9662;</span></div>'
    '<div class="body">'
    '<div class="stage">' + lands +
    '<svg class="arcs" width="820" height="640">' + paths + '</svg>' + pins +
    '<div class="stagebar"><span class="pill">가까운 곳</span>'
    '<span class="pill on">조금 더 멀리</span><span class="pill">아주 멀리</span></div>'
    '<div class="pop" style="left:%.1fpx;top:%.1fpx">%s</div>' % (OPEN["_x"], OPEN["_y"] - 15, detail(OPEN)) +
    '<div class="dock">'
    '<div class="fdrow"><span class="fdlabel">날짜</span><div class="chips">'
    '<span class="fchip on">아무때</span><span class="fchip">이번 주</span>'
    '<span class="fchip">이번 주말</span><span class="fchip">다음 달</span>'
    '<span class="fchip">날짜 지정</span></div></div>'
    '<div class="fdrow"><span class="fdlabel">분위기</span><div class="chips">'
    '<span class="fchip">해변</span><span class="fchip">도시</span>'
    '<span class="fchip new">문화</span><span class="fchip">미식</span>'
    '<span class="fchip">자연</span><span class="fchip">온천</span></div></div>'
    '<div class="fdrow"><span class="fdlabel">예산</span>'
    '<span class="brange"><i></i></span><span class="bval">74만 이하</span></div>'
    '</div></div>'
    '<div class="panel">'
    '<div class="fhead"><b>오늘의 발견</b><span>서울 출발 · ' + str(len(ALL)) + '곳</span></div>'
    '<div class="sortbar"><span class="spill on">가성비순</span>'
    '<span class="spill">임박순</span><span class="spill">할인율순</span></div>'
    '<div class="feed">' + hero_card(HERO) +
    "".join(small_card(d, on=(d is OPEN)) for d in FEED) +
    '</div><div class="cut"></div></div>'
    '</div></div>')

ROWS = [
    (1, False, "거리 단계 3버튼 · 담백한 라벨",
     "<code>가까운 곳 / 조금 더 멀리 / 아주 멀리</code>. 자유 줌·팬은 안 넣는다 — "
     "정해주는 서비스라 뷰도 우리가 정한다. <b>현행 코드는 아직 <code>＋ 동남아 / ＋ 유럽·미주</code>다</b>(프론트 CH1).",
     "2026-08-22"),
    (2, False, "상세는 지도 위에 뜬다 (E1)",
     "카드를 누르면 <b>지도가 그 핀으로 미끄러진 뒤</b> 카드가 핀에서 피어난다. "
     "움직임이 시선을 데려가므로 &lsquo;어디로 가는지&rsquo;가 그대로 보인다. "
     "움직이는 목업은 <b>open.html</b>.", "2026-09-01"),
    (3, False, "핀이 커지고 이름표 · 항로 강조",
     "패널과 지도가 <b>각자 자기 언어로</b> 반응한다. 핀을 눌러도 대칭으로 동작한다 — "
     "패널이 그 카드로 스크롤한다.", "2026-09-01"),
    (4, False, "히어로는 사진 위에 태그",
     "사진이 전폭(104px)이라 태그를 담을 수 있다. 개수가 곧 <b>즐길 게 얼마나 많은가</b>다(2~4개 가변).",
     "2026-09-01"),
    (5, False, "작은 카드엔 태그 없음",
     "62px 썸네일은 태그를 담기엔 작다. 여기선 <b>어디·얼마·언제</b>만 읽으면 된다. "
     "카드가 <b>129px → 103px</b>이 되고 패널에 <b>+27%</b> 더 들어간다.", "2026-09-01"),
    (6, False, "도장 3티어 · 15/25/35%",
     "테두리 → 채움 → 그라디언트+후광. 오늘 <b>17/3/5건</b>(126건 중). "
     "30일 이력으로 검증해 임계값을 <b>유지</b>하기로 했다.", "2026-09-01"),
    (7, False, "직항 배지는 가격 줄 우측",
     "도장과 <b>형태를 다르게</b> 한다(둥근 청록 채움, 기울기 없음). "
     "근거리 직항은 당연해서 안 붙인다 — <b>중·장거리만</b>, 오늘 25건(20%).", "2026-08-22"),
    (8, False, "날짜는 두 단 위계",
     "출발일이 주 라인, <code>박수 · 시기</code>가 보조 라인. 글로만 늘어놓으면 안 읽힌다.",
     "2026-08-22"),
    (9, True, "필터 칩에 <code>문화</code>를 넣는다",
     "상위 어휘 6종이 곧 칩이다. <b>현행 마크업엔 <code>문화</code>가 빠져 있다</b> — "
     "52건짜리 2위 어휘다(C-14, 프론트 CH2).", "미반영"),
    (10, True, "필터 도크 위치는 <b>아직 안 정했다</b>",
     "지금은 지도 아래에 겹쳐 둔다(현행). 지도를 가리는 문제가 있어 PH5에서 정한다.",
     "미정"),
]

trs = ""
for n, q, title, desc, when in ROWS:
    trs += ('<tr><td class="k"><span class="num%s">%d</span>%s</td><td>%s</td>'
            '<td class="k" style="color:%s">%s</td></tr>'
            % (" q" if q else "", n, title, desc,
               "#6C7B78" if q else "#1E7A50", when))

html = (
    "<!doctype html><html lang=ko><head><meta charset=utf-8>"
    "<meta name=viewport content='width=device-width,initial-scale=1'>"
    "<title>갈래말래 — 확정 홈</title><style>" + CSS + "</style></head><body><div class=wrap>"
    "<h1>발견 홈 &mdash; <em>지금까지 정한 것</em></h1>"
    "<p class=lede>빈 상자가 아니라 <b>실제 딜</b>로 채웠다. 서울 출발 " + str(len(ALL)) + "건 중 "
    "&lsquo;조금 더 멀리&rsquo; 단계에 드는 " + str(len(STAGE)) + "곳을 실제 좌표로 그렸다. "
    "움직임은 없다 &mdash; 전환은 <b>open.html</b>에서 눌러볼 수 있다.<br>"
    "<b style='color:#17201F'>검은 번호</b>는 확정된 것, "
    "<b style='color:#17201F'>흰 번호</b>는 아직 안 정했거나 코드에 미반영인 것이다.</p>"
    + app +
    "<h2><span class=n>01</span>번호 설명</h2>"
    "<table><tr><th style='width:270px'>무엇을</th><th>내용</th><th style='width:92px'>확정일</th></tr>"
    + trs + "</table>"
    "<h2><span class=n>02</span>아직 안 정한 것</h2>"
    "<table><tr><th style='width:180px'>안건</th><th>메모</th></tr>"
    "<tr><td class=k>패널 폭</td><td>지금 <b>380px</b>. 넓히면 카드가 여유롭지만 <b>지도가 좁아져 지구가 작아진다</b> "
    "&mdash; 미주까지 담아야 해서(호 286.7&deg;) 무대 폭이 곧 배율이다. "
    "다만 <b>&lsquo;스르륵 이동&rsquo;이 확정돼</b> 처음부터 다 보일 필요는 줄었다.</td></tr>"
    "<tr><td class=k>필터 도크 위치</td><td>지금은 지도 위에 겹쳐 둔다(번호 10). 지도를 가린다.</td></tr>"
    "<tr><td class=k>화면0</td><td>출발지를 고르는 첫 화면을 지금처럼 <b>따로</b> 둘지, 지도 위에서 바로 고르게 할지.</td></tr>"
    "<tr><td class=k>모바일</td><td>지도와 카드 비중. 상세는 <b>하단 시트로 확정</b>(화면이 좁아 나란히 못 둔다).</td></tr>"
    "</table>"
    "<p class=note>&#9888; <b>이 세션엔 브라우저가 없어 실제 렌더를 못 본다.</b> "
    "배치가 어색하거나 겹치는 곳이 있으면 알려주면 고친다.</p>"
    "<p class=foot>생성 <b>design/build_home.py</b> &middot; 데이터 <b>docs/data/deals.json</b> "
    "(<code>updated " + D.get("updated", "") + "</code>) &middot; "
    "확정 스펙 <b>../SPEC.md</b> &middot; 근거 <b>../DECISIONS.md</b> &middot; "
    "움직임 <b>open.html</b> &middot; 밀도 <b>density.html</b></p>"
    "</div></body></html>")

out = os.path.join(BASE, "home.html")
io.open(out, "w", encoding="utf-8").write(html)
print("home.html  %.1fKB" % (len(html) / 1024.0))
print("  무대: '조금 더 멀리' %d곳 / 서울 전체 %d건" % (len(STAGE), len(ALL)))
print("  히어로: %s %s원 · 열린 상세: %s %s원 (%s)"
      % (HERO["ko"], money(HERO["price"]), OPEN["ko"], money(OPEN["price"]), tier(OPEN)))
print("  라벨(major): %s" % " · ".join(d["ko"] for d in LABELED))
