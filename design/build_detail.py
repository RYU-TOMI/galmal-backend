# -*- coding: utf-8 -*-
"""확장 상세 — "어떻게 띄우고 무엇을 보여주나".

현행 구현(discover.js showCard/place, discover.css .hc-*)을 먼저 읽고 그렸다.
사진 위 태그 규칙 통일안도 함께 담는다.
소유: 기획 세션. 산출물 design/detail.html
"""
import json, io, os
import sys, os as _os
sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))

BASE = os.path.dirname(os.path.abspath(__file__))
D = json.load(io.open(os.path.join(BASE, "..", "docs", "data", "deals.json"), encoding="utf-8"))

TOP = ["해변", "도시", "미식", "자연", "문화", "온천"]
SUB = {"리조트", "스노클링", "서핑", "섬", "야경", "쇼핑", "마천루", "골목",
       "야시장", "길거리음식", "화산", "트레킹", "사막", "폭포", "사원", "유적", "고성", "미술관"}
# 임계값은 _fmt.py 한 곳에만 둔다 — 여기서 다시 적으면 갈라진다(2026-09-01)
from _fmt import TIERS


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


deals = sorted([x for x in D["deals"] if x["o"] == "SEL"], key=lambda x: x["price"])
HERO = deals[0]
# 상세를 열어 보일 카드 — 도장·직항·태그가 다 붙은 걸로 고른다
OPEN = next((d for d in deals[1:] if tier(d) and len(card_tags(d["tags"])) >= 3),
            deals[3])
OTHERS = [d for d in deals[1:9] if d is not OPEN]

CSS = """
:root{--ink:#17201F;--sub:#6C7B78;--line:#E3EAE8;--soft:#F2F6F5;
 --accent:#F2603F;--coast:#2E7D74;--sea:#EAF1F0;--land:#DCE6E3}
*{box-sizing:border-box}
body{margin:0;font:14px/1.6 -apple-system,"Segoe UI",Roboto,"Malgun Gothic",sans-serif;
 color:var(--ink);background:var(--sea)}
.wrap{max-width:1400px;margin:0 auto;padding:44px 30px 90px}
h1{font-size:1.9rem;letter-spacing:-.03em;margin:0 0 6px}
h1 em{font-style:normal;color:var(--accent)}
.lede{color:var(--sub);margin:0 0 34px;max-width:800px;line-height:1.75}
h2{font-size:1.12rem;margin:54px 0 8px;display:flex;align-items:center;gap:10px}
h2 .n{font-size:.68rem;background:var(--ink);color:#fff;border-radius:5px;padding:2px 7px;font-weight:800}
h3{font-size:.95rem;margin:26px 0 8px}
.note{color:var(--sub);font-size:.88rem;line-height:1.75;margin:0 0 20px;max-width:880px}
.cols{display:flex;gap:18px;flex-wrap:wrap;align-items:flex-start}
.col{width:400px}
.chead{display:flex;align-items:baseline;gap:8px}
.cid{font-size:.66rem;font-weight:900;background:var(--ink);color:#fff;border-radius:4px;padding:2px 7px}
.cnm{font-weight:800;font-size:.94rem}
.rec{font-size:.56rem;font-weight:900;background:var(--accent);color:#fff;
 border-radius:4px;padding:2px 6px;vertical-align:2px}
.no{font-size:.56rem;font-weight:900;background:var(--sub);color:#fff;
 border-radius:4px;padding:2px 6px;vertical-align:2px}
.cdesc{color:var(--sub);font-size:.79rem;line-height:1.62;min-height:60px;margin:5px 0 10px}
.pm{display:flex;gap:6px;margin-bottom:9px;font-size:.68rem}
.pm b{color:#1E7A50}.pm i{font-style:normal;color:var(--accent)}
.pm div{flex:1;background:#fff;border:1px solid var(--line);border-radius:8px;padding:6px 8px;line-height:1.5}
/* 무대 + 패널 */
.shell{display:flex;width:400px;height:560px;border:1px solid var(--line);
 border-radius:14px;overflow:hidden;background:#fff}
.stage{flex:1;position:relative;background:var(--sea);min-width:0}
.stage .globe{position:absolute;inset:0;background:
 radial-gradient(120px 90px at 30% 34%,var(--land),transparent 70%),
 radial-gradient(90px 70px at 68% 62%,var(--land),transparent 70%),var(--sea)}
.pin{position:absolute;width:9px;height:9px;border-radius:99px;background:var(--accent);
 box-shadow:0 0 0 3px rgba(242,96,63,.22)}
.pin.big{width:15px;height:15px;box-shadow:0 0 0 6px rgba(242,96,63,.3);z-index:3}
.pinlab{position:absolute;font-size:.56rem;font-weight:800;color:var(--ink);
 background:#fff;border-radius:4px;padding:1px 5px;white-space:nowrap;box-shadow:0 1px 4px #0002}
.panel{width:190px;flex:none;background:var(--sea);border-left:1px solid var(--line);
 padding:0 8px;overflow:hidden;position:relative}
.sortbar{height:38px;display:flex;align-items:center;gap:4px;font-size:.54rem}
.spill{background:#fff;border:1px solid var(--line);border-radius:99px;padding:3px 7px;font-weight:800;color:var(--sub)}
.spill.on{background:var(--ink);color:#fff;border-color:var(--ink)}
.feed{display:flex;flex-direction:column;gap:7px}
/* 카드 */
.fcard{display:flex;gap:8px;background:#fff;border:1.5px solid var(--line);
 border-radius:11px;padding:8px;overflow:hidden}
.fcard.on{border-color:var(--accent);box-shadow:0 4px 14px rgba(242,96,63,.18)}
.thumb{flex:none;border-radius:8px;position:relative;overflow:hidden;
 background:linear-gradient(140deg,#cfe0dc,#e9efed)}
.fbody{flex:1;min-width:0;display:flex;flex-direction:column;justify-content:center}
.frow{display:flex;justify-content:space-between;align-items:center;gap:5px}
.fcity{font-size:.8rem;font-weight:900;letter-spacing:-.02em;line-height:1.25;
 white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.prow{display:flex;justify-content:space-between;align-items:center;gap:6px;margin-top:2px}
.price{font-weight:900;font-size:.94rem;line-height:1.2;letter-spacing:-.03em;font-variant-numeric:tabular-nums}
.price small{font-size:.62em;font-weight:700;color:var(--sub);margin-left:1px}
.dmain{font-size:.6rem;line-height:1.3;font-weight:800;margin-top:4px;font-variant-numeric:tabular-nums}
.dsub{font-size:.55rem;line-height:1.3;font-weight:700;color:var(--sub);margin-top:1px;font-variant-numeric:tabular-nums}
.wk{color:var(--sub);font-weight:700}
.bdg{font-size:.5rem;font-weight:800;border-radius:99px;padding:1px 6px;flex:none;
 background:var(--coast);color:#fff;white-space:nowrap}
.stamp{flex:none;font-weight:900;white-space:nowrap;border-radius:3px}
.stamp.t1{transform:rotate(-7deg);border:1.2px solid var(--accent);color:var(--accent);font-size:.46rem;padding:1px 4px;background:#fff}
.stamp.t2{transform:rotate(-8deg);background:var(--accent);color:#fff;font-size:.5rem;padding:1px 5px}
.stamp.t3{transform:rotate(-9deg);background:linear-gradient(135deg,#F2603F,#FF8A63 42%,#C6472A);
 color:#fff;font-size:.52rem;padding:1px 6px;box-shadow:0 0 0 1.5px #fff,0 0 0 3px rgba(242,96,63,.2)}
/* 사진 위 태그 — 통일 규칙 */
.phtags{position:absolute;left:5px;right:5px;bottom:5px;display:flex;gap:3px;flex-wrap:wrap}
.phtag{font-size:.5rem;font-weight:800;color:#fff;background:rgba(6,20,18,.5);
 backdrop-filter:blur(3px);border-radius:4px;padding:1px 5px;white-space:nowrap}
.cityover{position:absolute;left:8px;bottom:20px;color:#fff;font-weight:900;
 font-size:.9rem;text-shadow:0 1px 6px #0009;letter-spacing:-.02em}
/* hero */
.hero{flex-direction:column;gap:0;padding:0;overflow:hidden}
.hero .ph{width:100%;height:92px;position:relative;overflow:hidden;
 background:linear-gradient(140deg,#cfe0dc,#e9efed)}
.hero .hb{padding:8px}
.pick{position:absolute;left:7px;top:7px;background:#fff;color:var(--accent);font-weight:900;
 font-size:.52rem;padding:2px 6px;border-radius:99px}
/* 확장 상세 */
.det{background:#fff;border:1.5px solid var(--accent);border-radius:11px;overflow:hidden;
 box-shadow:0 8px 26px rgba(242,96,63,.2)}
.det .ph{width:100%;height:100px;position:relative;overflow:hidden;
 background:linear-gradient(140deg,#bcd3ce,#dde8e5)}
.det .db{padding:9px}
.dsec{font-size:.54rem;font-weight:800;color:var(--sub);margin:9px 0 5px;
 padding-top:8px;border-top:1px dashed var(--line)}
.cmp{display:flex;align-items:center;gap:6px;font-size:.56rem;margin:3px 0}
.cmp .bar{flex:1;height:6px;border-radius:99px;background:var(--soft);overflow:hidden}
.cmp .bar i{display:block;height:100%;border-radius:99px;background:var(--accent)}
.cmp .bar.mut i{background:#c3cfcc}
.cmp b{font-variant-numeric:tabular-nums;white-space:nowrap;font-size:.58rem}
.lnk{display:flex;justify-content:space-between;align-items:center;background:var(--soft);
 border-radius:7px;padding:5px 8px;font-size:.58rem;font-weight:800;margin-top:4px}
.lnk span.p{font-variant-numeric:tabular-nums}
.go{margin-top:7px;background:var(--accent);color:#fff;text-align:center;font-weight:800;
 font-size:.62rem;border-radius:8px;padding:7px 0}
.ad{font-size:.48rem;color:var(--sub);line-height:1.5;margin-top:6px;text-align:center}
.closex{position:absolute;right:6px;top:6px;width:18px;height:18px;border-radius:99px;
 background:rgba(6,20,18,.45);color:#fff;font-size:.6rem;font-weight:900;
 display:flex;align-items:center;justify-content:center}
.cut{position:absolute;left:0;right:0;bottom:0;height:60px;pointer-events:none;
 background:linear-gradient(transparent,var(--sea) 66%)}
/* 지도 위 플로팅(E1) */
.float{position:absolute;width:172px;z-index:5}
.float:after{content:"";position:absolute;left:50%;bottom:-6px;margin-left:-6px;
 border:6px solid transparent;border-top-color:#fff;filter:drop-shadow(0 2px 1px rgba(242,96,63,.3))}
/* 시트(E4) */
.sheet{position:absolute;left:0;right:0;bottom:0;z-index:5;padding:8px;
 background:var(--sea);border-top:1px solid var(--line);box-shadow:0 -8px 24px #0001}
.grab{width:34px;height:4px;border-radius:99px;background:#c3cfcc;margin:0 auto 7px}
table{width:100%;border-collapse:collapse;font-size:.86rem;background:#fff;
 border:1px solid var(--line);border-radius:12px;overflow:hidden}
th{text-align:left;font-weight:700;font-size:.74rem;color:var(--sub);padding:11px 12px;
 border-bottom:1px solid var(--line);background:var(--soft)}
td{padding:11px 12px;border-bottom:1px solid var(--line);vertical-align:top}
tr:last-child td{border-bottom:0}
.ok{color:#1E7A50;font-weight:800}.bad{color:var(--accent);font-weight:800}
.callout{background:#fff;border:1px solid var(--line);border-left:3px solid var(--accent);
 border-radius:10px;padding:16px 18px;margin:20px 0;font-size:.92rem;line-height:1.8;max-width:900px}
.callout b{color:var(--accent)}
ul.k{margin:12px 0 0;padding-left:19px;color:var(--sub);font-size:.89rem;max-width:900px}
ul.k li{margin:8px 0}ul.k b{color:var(--ink)}
code{font-family:ui-monospace,Consolas,monospace;font-size:.85em;background:var(--soft);padding:1px 5px;border-radius:4px}
.foot{margin-top:60px;padding-top:18px;border-top:1px solid var(--line);font-size:.8rem;color:var(--sub)}
"""


def phtags(d, n=4):
    return ('<div class="phtags">%s</div>'
            % "".join('<span class="phtag">%s</span>' % t for t in card_tags(d["tags"])[:n]))


def small_card(d, on=False):
    """작은 카드 — 태그 없음(2026-09-01 확정). 썸네일 52px."""
    t = tier(d)
    stamp = ('<span class="stamp %s">%d%%&darr;</span>' % (t, d["discount"])) if t else ""
    bdg = '<span class="bdg">&#9992;</span>' if direct(d) else ""
    return ('<div class="fcard%s"><div class="thumb" style="width:52px;height:52px"></div>'
            '<div class="fbody">'
            '<div class="frow"><span class="fcity">%s</span>%s</div>'
            '<div class="prow"><span class="price">%s<small>원</small></span>%s</div>'
            '<div class="dmain">%s</div><div class="dsub">%s</div>'
            '</div></div>'
            % (" on" if on else "", d["ko"], stamp, money(d["price"]), bdg,
               d["dep"], d.get("nights", "")))


def hero_card(d):
    """히어로 — 사진 92px, 사진 위 태그."""
    t = tier(d)
    stamp = ('<span class="stamp %s">%d%%&darr;</span>' % (t, d["discount"])) if t else ""
    return ('<div class="fcard hero"><div class="ph">'
            '<span class="pick">오늘의 발견</span>%s'
            '<span class="cityover">%s</span></div>'
            '<div class="hb"><div class="prow" style="margin-top:0">'
            '<span class="price">%s<small>원</small></span>%s</div>'
            '<div class="dmain">%s <span class="wk">&middot; %s</span></div></div></div>'
            % (phtags(d), d["ko"], money(d["price"]), stamp,
               d["dep"], d.get("nights", "")))


def detail_card(d, close=True):
    """확장 상세 — 사진 100px + 사진 위 태그 + 시세 비교 + 예약처."""
    t = tier(d)
    stamp = ('<span class="stamp %s">%d%%&darr;</span>' % (t, d["discount"])) if t else ""
    bdg = '<span class="bdg">&#9992; 직항</span>' if direct(d) else ""
    med = d.get("median") or int(d["price"] * 1.25)
    ratio = min(1.0, d["price"] / float(med)) if med else 1.0
    links = (d.get("links") or [])[:3]
    lnk = "".join('<div class="lnk"><span>%s</span><span class="p">%s원</span></div>'
                  % (l.get("name", "예약처"), money(l.get("price", d["price"])))
                  for l in links) or ('<div class="lnk"><span>비교 사이트</span>'
                                      '<span class="p">%s원</span></div>' % money(d["price"]))
    x = '<span class="closex">&times;</span>' if close else ""
    return ('<div class="det"><div class="ph">%s%s<span class="cityover">%s</span></div>'
            '<div class="db">'
            '<div class="prow" style="margin-top:0">'
            '<span class="price" style="font-size:1.06rem">%s<small>원</small></span>%s</div>'
            '<div class="prow" style="margin-top:3px">'
            '<span class="dmain" style="margin-top:0">%s <span class="wk">&middot; %s</span></span>%s</div>'
            '<div class="dsec">평소 시세와 비교</div>'
            '<div class="cmp"><span style="width:40px;color:var(--sub)">평소</span>'
            '<span class="bar mut"><i style="width:100%%"></i></span><b>%s원</b></div>'
            '<div class="cmp"><span style="width:40px;font-weight:800">지금</span>'
            '<span class="bar"><i style="width:%d%%"></i></span><b>%s원</b></div>'
            '<div class="dsec">어디가 제일 싼지 비교해보세요</div>%s'
            '<div class="go">갈래 &rarr; 예약처로</div>'
            '<div class="ad">위 가격은 발견가(스캔 시점) · 실시간 최저가는 각 사이트에서 확인하세요<br>'
            '일부는 예약 시 수수료 (광고)</div>'
            '</div></div>'
            % (x, phtags(d), d["ko"], money(d["price"]), stamp,
               d["dep"], d.get("nights", ""), bdg,
               money(med), int(ratio * 100), money(d["price"]), lnk))


def stage(pins_on, label=None, extra=""):
    pts = [(28, 30), (46, 22), (62, 44), (38, 58), (70, 66), (54, 74)]
    ps = ""
    for i, (l, tp) in enumerate(pts):
        big = (i == 2 and pins_on)
        ps += '<span class="pin%s" style="left:%d%%;top:%d%%"></span>' % (" big" if big else "", l, tp)
        if big and label:
            ps += '<span class="pinlab" style="left:%d%%;top:%d%%">%s</span>' % (l + 4, tp - 2, label)
    return '<div class="stage"><div class="globe"></div>%s%s</div>' % (ps, extra)


# ── E1 지도 위 플로팅(현행) ───────────────────────────────────
e1 = ('<div class="shell">'
      + stage(True, None,
              '<div class="float" style="left:34%;top:14%">' + detail_card(OPEN) + '</div>')
      + '<div class="panel"><div class="sortbar"><span class="spill on">가성비순</span>'
        '<span class="spill">임박순</span></div><div class="feed">'
      + hero_card(HERO) + "".join(small_card(d, on=(d is OPEN)) for d in deals[1:7])
      + '</div><div class="cut"></div></div></div>')

# ── E2 패널 안 인라인 확장 ────────────────────────────────────
feed2 = [hero_card(HERO)]
for d in deals[1:7]:
    if d is OPEN:
        feed2.append(detail_card(OPEN))
    else:
        feed2.append(small_card(d))
e2 = ('<div class="shell">' + stage(True, OPEN["ko"])
      + '<div class="panel"><div class="sortbar"><span class="spill on">가성비순</span>'
        '<span class="spill">임박순</span></div><div class="feed">'
      + "".join(feed2) + '</div><div class="cut"></div></div></div>')

# ── E3 패널 전체 교체 ─────────────────────────────────────────
e3 = ('<div class="shell">' + stage(True, OPEN["ko"])
      + '<div class="panel"><div class="sortbar">'
        '<span class="spill on">&larr; 목록으로</span></div>'
        '<div class="feed">' + detail_card(OPEN, close=False) + '</div></div></div>')

# ── E4 패널 위 시트 ───────────────────────────────────────────
e4 = ('<div class="shell">' + stage(True, OPEN["ko"])
      + '<div class="panel"><div class="sortbar"><span class="spill on">가성비순</span>'
        '<span class="spill">임박순</span></div><div class="feed">'
      + hero_card(HERO) + "".join(small_card(d) for d in deals[1:5])
      + '</div><div class="sheet"><div class="grab"></div>'
      + detail_card(OPEN) + '</div></div></div>')

OPTS = [
    ("E1", "지도 위 플로팅", "현행", e1, "no",
     "핀 옆에 뜬다. <b>지도와 딜의 연결은 가장 강하다.</b><br>"
     "하지만 <b>오른쪽을 눌렀는데 가운데가 반응</b>해 시선이 튀고, 지도를 가린다. "
     "핀이 화면 밖이면(B14) 뜰 자리가 없다.",
     [("지도 연결", 1), ("시선 유지", 0), ("공간", 0), ("딥링크", 0)]),
    ("E2", "패널 안에서 펼치기", "추천", e2, "rec",
     "누른 카드가 <b>그 자리에서</b> 펼쳐진다. 스크롤 위치가 유지되고 위아래 딜이 계속 보인다.<br>"
     "지도는 <b>핀을 키우고 이름을 띄워</b> 각자 자기 언어로 답한다.",
     [("지도 연결", 1), ("시선 유지", 1), ("공간", 1), ("딥링크", 1)]),
    ("E3", "패널을 상세로 교체", "", e3, "",
     "패널이 통째로 상세가 된다. 공간이 가장 넉넉하다.<br>"
     "대신 <b>피드 맥락이 사라져</b> 다음 딜로 넘어가려면 매번 목록으로 돌아가야 한다. "
     "&lsquo;둘러보기&rsquo;가 &lsquo;검색&rsquo;이 된다.",
     [("지도 연결", 1), ("시선 유지", 0), ("공간", 1), ("딥링크", 1)]),
    ("E4", "패널 위 시트", "", e4, "",
     "아래에서 덮어 올라온다. 모바일에서 익숙한 패턴이고 <b>현행 모바일이 이미 이 방식</b>이다.<br>"
     "데스크톱에선 <b>덮인 카드가 안 보여</b> 비교가 끊긴다. 패널이 좁을수록 손해가 크다.",
     [("지도 연결", 1), ("시선 유지", 0), ("공간", 1), ("딥링크", 1)]),
]

cols = []
for oid, name, badge, mock, cls, desc, marks in OPTS:
    b = ""
    if badge == "현행":
        b = '<span class="no">현행</span>'
    elif badge == "추천":
        b = '<span class="rec">추천</span>'
    pm = "".join('<div>%s %s</div>'
                 % (("<b>&#10003;</b>" if v else "<i>&times;</i>"), k) for k, v in marks)
    cols.append('<div class="col"><div class="chead"><span class="cid">%s</span>'
                '<span class="cnm">%s</span>%s</div>'
                '<div class="cdesc">%s</div><div class="pm">%s</div>%s</div>'
                % (oid, name, b, desc, pm, mock))

html = (
    "<!doctype html><html lang=ko><head><meta charset=utf-8>"
    "<meta name=viewport content='width=device-width,initial-scale=1'>"
    "<title>갈래말래 — 확장 상세</title><style>" + CSS + "</style></head><body><div class=wrap>"
    "<h1>확장 상세 — <em>어떻게 띄우고 뭘 보여주나</em></h1>"
    "<p class=lede>서울 출발 실제 딜로 그렸다. 열어 보인 카드는 <b>" + OPEN["ko"] + "</b>. "
    "현행 구현(<code>discover.js</code> <code>showCard</code>/<code>place</code>, "
    "<code>.hc-*</code>)을 먼저 읽고 만들었다.</p>"

    "<h2><span class=n>01</span>사진 위 태그 — 통일 규칙</h2>"
    "<p class=note>사진이 있는 자리에는 <b>사진 위에</b> 태그를 얹고, 작은 썸네일에는 <b>태그를 넣지 않는다.</b> "
    "(2026-09-01 확정) 태그가 세로를 안 먹으니 작은 카드가 <b>129px &rarr; 103px</b>로 줄어든다.</p>"
    "<table><tr><th>자리</th><th>사진</th><th>태그</th><th>이유</th></tr>"
    "<tr><td><b>작은 카드</b></td><td>52&ndash;62px 썸네일</td><td class=bad>없음</td>"
    "<td>사진이 태그를 담기엔 너무 작다. 여기선 <b>어디&middot;얼마&middot;언제</b>만 읽으면 된다</td></tr>"
    "<tr><td><b>히어로</b>(오늘의 발견)</td><td>92px 전폭</td><td class=ok>사진 위 2&ndash;4개</td>"
    "<td>&lsquo;오늘은 여기&rsquo;라는 답이라 <b>왜 여기인지</b>까지 보여준다</td></tr>"
    "<tr><td><b>확장 상세</b></td><td>100px 전폭</td><td class=ok>사진 위 2&ndash;4개</td>"
    "<td>결정하는 자리. 개수가 곧 <b>즐길 게 얼마나 많은가</b>다</td></tr></table>"
    "<p class=note>&#9888; <b>잃는 것을 적어둔다.</b> 작은 카드에서 태그가 빠지면 "
    "&lsquo;태그 개수 = 즐길 거리&rsquo; 신호를 <b>스크롤 중에는 못 읽는다.</b> "
    "그 신호는 이제 <b>히어로와 상세에서만</b> 살아 있다. 사용자가 밀도를 택했고, 근거를 남긴다.</p>"

    "<h2><span class=n>02</span>어떻게 띄우나 &mdash; 후보 넷</h2>"
    "<p class=note>패널 폭은 비교를 위해 좁게(190px) 그렸다. 실제는 380px이라 상세가 더 넉넉하다.</p>"
    "<div class=cols>" + "".join(cols) + "</div>"

    "<h2><span class=n>03</span>왜 E2인가</h2>"
    "<div class=callout><b>누른 곳이 반응해야 한다.</b><br>"
    "지금은 <b>오른쪽 패널을 눌렀는데 가운데 지도 위에서</b> 카드가 뜬다(E1). "
    "시선이 튀고, 방금 보던 딜들이 가려지고, 핀이 화면 밖이면 뜰 자리조차 애매하다.<br>"
    "E2는 <b>카드가 그 자리에서 펼쳐지고</b>, 지도는 <b>핀을 키워</b> 답한다. "
    "두 곳이 각자 자기 언어로 반응하지, 한쪽이 다른 쪽 자리를 빼앗지 않는다.</div>"
    "<ul class=k>"
    "<li><b>스크롤 위치가 유지된다.</b> 위아래 딜이 계속 보이니 &lsquo;둘러보기&rsquo;가 안 끊긴다. "
    "발견 서비스에서 비교는 핵심이다.</li>"
    "<li><b>지도를 안 가린다.</b> 상세를 연 채로 다른 핀을 볼 수 있다.</li>"
    "<li><b>B14와 안 엮인다.</b> 핀이 화면 밖이어도 상세는 패널에서 열린다. "
    "E1은 뜰 자리를 핀에 의존해서 그 버그와 묶여 있었다.</li>"
    "<li><b>딥링크가 자연스럽다.</b> <code>#SEL-" + OPEN["d"] + "</code>로 들어오면 "
    "그 카드를 펼친 채 스크롤해 주면 끝이다.</li>"
    "<li><b>모바일은 그대로 시트(E4)</b>다. 화면이 좁아 나란히 못 두니 덮는 게 맞다. "
    "현행 <code>innerWidth &lt;= 860</code> 분기를 유지한다.</li>"
    "</ul>"

    "<h2><span class=n>04</span>열고 닫기</h2>"
    "<table><tr><th>동작</th><th>결과</th></tr>"
    "<tr><td>작은 카드를 누른다</td><td>그 자리에서 펼쳐진다 + 지도 핀이 커지고 이름표가 뜬다 + "
    "<code>pushState</code> <code>#SEL-" + OPEN["d"] + "</code></td></tr>"
    "<tr><td>다른 카드를 누른다</td><td>먼저 것이 접히고 새 것이 펼쳐진다 <b>(동시에 하나만)</b></td></tr>"
    "<tr><td>지도 핀을 누른다</td><td>패널이 그 카드로 <b>스크롤</b>하며 펼친다 &mdash; 반대 방향도 같은 규칙</td></tr>"
    "<tr><td>× 또는 같은 카드 다시</td><td>접힌다 + <code>#SEL</code>로 되돌린다</td></tr>"
    "<tr><td>브라우저 뒤로가기</td><td><b>사이트를 안 떠나고</b> 상세만 닫힌다</td></tr>"
    "<tr><td>정렬&middot;필터를 바꾼다</td><td>펼친 것을 접는다 (현행 <code>collapse()</code>와 같다)</td></tr>"
    "<tr><td>그 딜이 오늘 사라졌다</td><td>출발지만 적용하고 안내 문구 &mdash; <b>F5</b>, "
    "다른 허브에 같은 목적지가 있으면 제안한다</td></tr></table>"

    "<p class=foot>생성 <b>design/build_detail.py</b> &middot; 데이터 <b>docs/data/deals.json</b>"
    "(서울 " + str(len(deals)) + "건) &middot; 확정 스펙 <b>../SPEC.md</b> &sect;CH4 &middot; "
    "현행 구현 <b>docs/assets/discover.js</b></p>"
    "</div></body></html>")

out = os.path.join(BASE, "detail.html")
io.open(out, "w", encoding="utf-8").write(html)
print("detail.html  %.1fKB" % (len(html) / 1024.0))
print("  열어 보인 카드: %s  %s원  tier=%s  tags=%s"
      % (OPEN["ko"], money(OPEN["price"]), tier(OPEN), "/".join(card_tags(OPEN["tags"]))))
print("  후보 %d개 · 서울 %d건" % (len(OPTS), len(deals)))
