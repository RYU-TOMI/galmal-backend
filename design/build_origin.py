# -*- coding: utf-8 -*-
"""화면0 — 출발지를 어떻게 고르게 할까.

현행(discover.js:262~284)은 전체 화면 인트로다. 한국 지도에 핀 넷을 찍고
고르면 `#intro`가 숨는다. 실제 허브 딜 수로 그린다.
소유: 기획 세션. 산출물 design/origin.html
"""
import json, io, os, sys

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
from _app import CSS
from _fmt import money, tier, direct, daterange, datesub

D = json.load(io.open(os.path.join(BASE, "..", "docs", "data", "deals.json"), encoding="utf-8"))
deals = D["deals"]
N = len(deals)

HUBS = []
for code, o in D["origins"].items():
    ds = [d for d in deals if d["o"] == code]
    if not ds:
        continue
    HUBS.append({"code": code, "name": o["name"], "lat": o["lat"], "lon": o["lon"],
                 "n": len(ds), "best": min(ds, key=lambda x: x["price"])})
HUBS.sort(key=lambda h: -h["n"])
SPARSE = 10   # SPEC §CH2 — 딜 10건 미만은 희소

# ── 한국 지도 투영 ─────────────────────────────────────────────
KW, KH = 300, 380
lons = [h["lon"] for h in HUBS]
lats = [h["lat"] for h in HUBS]
lon0, lat0 = (min(lons) + max(lons)) / 2.0, (min(lats) + max(lats)) / 2.0
K = min((KW - 130) / max(.01, max(lons) - min(lons)),
        (KH - 150) / max(.01, max(lats) - min(lats)))
for h in HUBS:
    h["x"] = KW / 2.0 + (h["lon"] - lon0) * K
    h["y"] = KH / 2.0 - (h["lat"] - lat0) * K

EXTRA = """
.wrapZ{max-width:1180px;margin:0 auto;padding:44px 26px 90px}
.zrow{display:flex;gap:20px;flex-wrap:wrap;align-items:flex-start;margin:16px 0 34px}
.zc{width:368px}
.zhd{display:flex;align-items:baseline;gap:8px}
.zid{font-size:.64rem;font-weight:900;background:var(--ink);color:#fff;border-radius:4px;padding:2px 7px}
.znm{font-weight:800;font-size:.92rem}
.rec{font-size:.55rem;font-weight:900;background:var(--accent);color:#fff;border-radius:4px;padding:2px 6px;vertical-align:2px}
.no{font-size:.55rem;font-weight:900;background:var(--sub);color:#fff;border-radius:4px;padding:2px 6px;vertical-align:2px}
.zdesc{color:var(--sub);font-size:.78rem;line-height:1.62;min-height:74px;margin:5px 0 10px}
.frame{width:368px;height:400px;border:1px solid #cfdad7;border-radius:14px;overflow:hidden;
 position:relative;background:#fff}
.wmap{position:absolute;inset:0;background:
 radial-gradient(110px 80px at 26% 30%,var(--land),transparent 70%),
 radial-gradient(90px 66px at 68% 54%,var(--land),transparent 70%),
 radial-gradient(70px 54px at 40% 74%,var(--land),transparent 70%),var(--sea)}
.wpin{position:absolute;width:8px;height:8px;margin:-4px 0 0 -4px;border-radius:99px;
 background:var(--accent);box-shadow:0 0 0 3px rgba(242,96,63,.18)}
.blur{position:absolute;inset:0;backdrop-filter:blur(2px);background:rgba(234,241,240,.55)}
/* 전체 화면 인트로 */
.intro{position:absolute;inset:0;background:var(--sea);display:flex;
 flex-direction:column;align-items:center;padding:26px 20px}
.ititle{font-size:1.06rem;font-weight:900;letter-spacing:-.03em;text-align:center}
.isub{font-size:.74rem;color:var(--sub);font-weight:700;margin-top:5px;text-align:center}
.kmap{position:relative;width:300px;height:380px;margin-top:6px}
.kland{position:absolute;left:52px;top:44px;width:196px;height:290px;background:var(--land);
 border-radius:44% 52% 38% 60%/34% 30% 62% 66%}
.kpin{position:absolute;transform:translate(-50%,-50%);display:flex;flex-direction:column;
 align-items:center;gap:4px}
.kdot{width:13px;height:13px;border-radius:99px;background:var(--accent);
 box-shadow:0 0 0 4px rgba(242,96,63,.2),0 2px 6px #0002}
.klab{background:#fff;border:1px solid var(--line);border-radius:99px;padding:3px 10px;
 font-size:.72rem;font-weight:800;white-space:nowrap;box-shadow:0 2px 7px #0002;
 display:inline-flex;align-items:baseline;gap:5px}
.klab .n{font-size:.62rem;color:var(--sub);font-weight:700;font-variant-numeric:tabular-nums}
.klab.sp{border-style:dashed}
.klab.sp .n{color:var(--accent)}
/* 시트형 */
.osheet{position:absolute;left:14px;right:14px;bottom:14px;background:#fff;
 border:1px solid var(--line);border-radius:15px;padding:14px 15px 15px;
 box-shadow:0 -12px 34px rgba(16,44,38,.2)}
.ohd{font-size:.94rem;font-weight:900;letter-spacing:-.02em}
.osub{font-size:.7rem;color:var(--sub);font-weight:700;margin-top:3px}
.ogrid{display:grid;grid-template-columns:1fr 1fr;gap:7px;margin-top:11px}
.obtn{border:1px solid var(--line);border-radius:11px;padding:9px 11px;background:var(--soft);
 display:flex;align-items:baseline;justify-content:space-between;gap:6px}
.obtn b{font-size:.86rem;font-weight:900;letter-spacing:-.02em}
.obtn .n{font-size:.66rem;color:var(--sub);font-weight:700;font-variant-numeric:tabular-nums}
.obtn.sp{border-style:dashed}
.obtn.sp .n{color:var(--accent)}
.obtn.on{background:var(--accent);border-color:var(--accent)}
.obtn.on b,.obtn.on .n{color:#fff}
/* 헤더 */
.hdr2{position:absolute;left:0;right:0;top:0;height:46px;background:#fff;
 border-bottom:1px solid var(--line);display:flex;align-items:center;gap:14px;padding:0 13px;z-index:5}
.logo2{font-weight:900;font-size:.9rem;letter-spacing:-.03em}
.logo2 i{font-style:normal;color:var(--accent)}
.pill0{margin-left:auto;background:var(--soft);border:1px solid var(--line);border-radius:99px;
 padding:4px 11px;font-size:.72rem;font-weight:800}
.pill0.hi{background:var(--accent);color:#fff;border-color:var(--accent)}
.mini2{position:absolute;left:0;right:0;bottom:0;background:var(--sea);
 border-top:1px solid var(--line);padding:8px;display:flex;flex-direction:column;gap:7px}
.fcard{display:flex;gap:9px;background:#fff;border:1.5px solid var(--line);
 border-radius:11px;padding:8px}
.thumb{flex:none;width:46px;height:46px;border-radius:8px;
 background:linear-gradient(140deg,#cfe0dc,#e9efed)}
.fbody{flex:1;min-width:0}
.fcity{font-size:.84rem;font-weight:900;letter-spacing:-.02em}
.price{font-weight:900;font-size:.98rem;letter-spacing:-.03em;font-variant-numeric:tabular-nums}
.price small{font-size:.6em;font-weight:700;color:var(--sub)}
.dsub{font-size:.6rem;font-weight:700;color:var(--sub);margin-top:2px}
.mt2{display:flex;gap:7px;margin:9px 0 0}
.mt2 div{flex:1;background:#fff;border:1px solid var(--line);border-radius:9px;
 padding:7px 8px;text-align:center;font-size:.63rem;color:var(--sub);font-weight:700;line-height:1.4}
.mt2 b{display:block;font-size:1.02rem;letter-spacing:-.02em;color:var(--ink)}
.mt2 .g b{color:#1E7A50}.mt2 .r b{color:var(--accent)}
/* 헤더 알약 3안 */
.pill0.quiet{background:var(--soft);border-color:var(--line);color:var(--ink)}
.pill0.loud{background:#fff;border:1.5px solid var(--accent);color:var(--accent);font-weight:900}
.hint{position:absolute;left:0;right:0;top:46px;z-index:5;background:#FFF4F1;
 border-bottom:1px solid #F6C9BB;padding:7px 13px;display:flex;align-items:center;gap:8px;
 font-size:.72rem;font-weight:700;color:var(--ink)}
.hint b{color:var(--accent)}
.hint .x{margin-left:auto;color:var(--sub);font-weight:900}
.caret{position:absolute;right:16px;top:44px;width:0;height:0;z-index:6;
 border:7px solid transparent;border-bottom-color:#fff;filter:drop-shadow(0 -2px 2px #0001)}
.odrop{position:absolute;right:13px;top:56px;width:196px;background:#fff;border:1px solid var(--line);
 border-radius:12px;padding:9px 10px;z-index:6;box-shadow:0 12px 30px rgba(16,44,38,.2)}
.odrop .t{font-size:.62rem;font-weight:800;color:var(--sub);margin-bottom:6px}
.odrop .r2{display:flex;align-items:baseline;justify-content:space-between;
 padding:6px 8px;border-radius:7px;font-size:.78rem;font-weight:800}
.odrop .r2.on{background:var(--accent);color:#fff}
.odrop .r2 .n{font-size:.64rem;color:var(--sub);font-weight:700;font-variant-numeric:tabular-nums}
.odrop .r2.on .n{color:#fff9}
"""


def kmap(show_counts=True):
    out = '<div class="kmap"><div class="kland"></div>'
    for h in HUBS:
        sp = " sp" if h["n"] < SPARSE else ""
        cnt = ('<span class="n">%d곳</span>' % h["n"]) if show_counts else ""
        out += ('<div class="kpin" style="left:%.0fpx;top:%.0fpx">'
                '<span class="kdot"></span>'
                '<span class="klab%s">%s%s</span></div>'
                % (h["x"], h["y"], sp, h["name"], cnt))
    return out + '</div>'


WORLD = ('<div class="wmap"></div>'
         + "".join('<span class="wpin" style="left:%d%%;top:%d%%"></span>' % g
                   for g in [(24, 30), (38, 22), (56, 42), (32, 58), (68, 62), (48, 72),
                             (72, 34), (60, 76), (28, 44)]))


def frame(inner):
    return '<div class="frame">' + inner + '</div>'


# ── Z0 현행 ────────────────────────────────────────────────────
Z0 = frame('<div class="intro">'
           '<div class="ititle">어디서 출발해요?</div>'
           '<div class="isub">출발 공항을 고르면 오늘 싼 곳들이 열려요</div>'
           + kmap(show_counts=False) + '</div>')

# ── Z1 현행 + 건수 ─────────────────────────────────────────────
Z1 = frame('<div class="intro">'
           '<div class="ititle">어디서 출발해요?</div>'
           '<div class="isub">오늘 ' + str(N) + '곳이 열려 있어요</div>'
           + kmap() + '</div>')

# ── Z2 지도 위 시트 ────────────────────────────────────────────
grid = ""
for h in HUBS:
    sp = " sp" if h["n"] < SPARSE else ""
    on = " on" if h["code"] == "SEL" else ""
    grid += ('<div class="obtn%s%s"><b>%s</b><span class="n">%d곳</span></div>'
             % (sp, on, h["name"], h["n"]))
Z2 = frame(WORLD + '<div class="blur"></div>'
           + '<div class="hdr2"><span class="logo2">갈래<i>말래</i></span></div>'
           + '<div class="osheet"><div class="ohd">어디서 출발해요?</div>'
             '<div class="osub">오늘 ' + str(N) + '곳이 열려 있어요</div>'
             '<div class="ogrid">' + grid + '</div></div>')


# ── Z3 화면0 없음 ──────────────────────────────────────────────
def mini_card(d):
    return ('<div class="fcard"><div class="thumb"></div><div class="fbody">'
            '<div class="fcity">%s</div>'
            '<div class="price">%s<small>원</small></div>'
            '<div class="dsub">%s</div></div></div>'
            % (d["ko"], money(d["price"]), datesub(d)))


sel = [d for d in deals if d["o"] == "SEL"]
sel.sort(key=lambda x: x["price"])
Z3 = frame(WORLD
           + '<div class="hdr2"><span class="logo2">갈래<i>말래</i></span>'
             '<span class="pill0 hi">서울 출발 &#9662;</span></div>'
           + '<div class="mini2">' + "".join(mini_card(d) for d in sel[:3]) + '</div>')

def z3(pill_cls, extra="", label="서울 출발"):
    return frame(WORLD
                 + '<div class="hdr2"><span class="logo2">갈래<i>말래</i></span>'
                   '<span class="pill0 ' + pill_cls + '">' + label + ' &#9662;</span></div>'
                 + extra
                 + '<div class="mini2">' + "".join(mini_card(d) for d in sel[:3]) + '</div>')


P1 = z3("quiet")
P2 = z3("loud", '<div class="hint">지금 <b>서울 출발</b>로 보고 있어요'
                '<span style="color:var(--accent);font-weight:900">&nbsp;바꾸기</span>'
                '<span class="x">&times;</span></div>')
_rows = "".join('<div class="r2%s"><span>%s</span><span class="n">%d곳</span></div>'
                % (" on" if h["code"] == "SEL" else "", h["name"], h["n"]) for h in HUBS)
P3 = z3("loud", '<div class="caret"></div><div class="odrop">'
                '<div class="t">어디서 출발해요?</div>' + _rows + '</div>')

PILLS = [
    ("P1", "조용한 알약", "현행 스타일", "no", P1,
     "지금 헤더에 있는 회색 알약 그대로. <b>있는지도 모르고 지나칠 수 있다</b> &mdash; "
     "부산 사람이 &lsquo;서울 전용 서비스인가&rsquo;로 읽으면 그대로 이탈한다.",
     ["0클릭", "눈에 안 띔", "이탈 위험"]),
    ("P2", "코랄 알약 + 한 줄 안내", "추천", "rec", P2,
     "알약을 <b>코랄 테두리</b>로 올리고, <b>첫 방문에만</b> 한 줄 띠를 띄운다.<br>"
     "<b>막지 않는다</b> &mdash; 뒤에 딜이 이미 보이고, 닫으면 다시 안 뜬다.",
     ["0클릭", "눈에 띔", "안 막음"]),
    ("P3", "코랄 알약 + 드롭다운 열어둠", "", "", P3,
     "첫 방문에 목록을 <b>미리 펼쳐</b> 둔다. 가장 확실히 보이지만 "
     "<b>딜을 가린다</b> &mdash; 결국 작아진 화면0이다.",
     ["0클릭", "가장 잘 띔", "일부 가림"]),
]

OPTS = [
    ("Z0", "전체 화면 인트로", "기각", "no", Z0,
     "한국 지도에 핀 넷. <b>고르기 전엔 아무것도 안 보인다.</b><br>"
     "<b>몇 곳이 열려 있는지도 안 알려준다</b> &mdash; 제주를 골랐다가 8곳뿐인 걸 그때 안다.",
     ["1클릭", "매번", "제품 이해 ◎"]),
    ("Z1", "전체 화면 + 건수", "기각", "no", Z1,
     "같은 구조에 <b>딜 수를 붙였다.</b> 희소 허브(10곳 미만)는 <b>점선</b>으로 표시한다.<br>"
     "고르기 전에 <b>무엇을 고르는지</b> 안다. 하지만 여전히 <b>지도를 통째로 가린다.</b>",
     ["1클릭", "매번", "제품 이해 ◎"]),
    ("Z2", "지도 위 시트 + 기억", "기각", "no", Z2,
     "<b>제품이 뒤에 보인다.</b> 세계 지도와 핀이 흐릿하게 깔린 채 시트가 묻는다 &mdash; "
     "&lsquo;여긴 지도로 여행지를 찾는 곳이구나&rsquo;가 <b>고르기 전에</b> 전달된다.<br>"
     "고른 출발지는 <b>기억한다</b> &mdash; 다음부터 이 시트가 안 뜬다.",
     ["1클릭", "첫 방문만", "제품 이해 ◎"]),
    ("Z3", "화면0 없음 &mdash; 서울 기본", "확정", "rec", Z3,
     "바로 홈이 뜬다. <b>딜을 보여주는 것 자체가 가장 좋은 제품 설명</b>이다 &mdash; "
     "<code>어디서 출발해요?</code>는 아무 가치도 안 준 채 질문부터 한다.<br>"
     "남는 문제는 하나 &mdash; <b>서울이 아닌 45%가 바꾸는 버튼을 찾느냐.</b> &sect;02에서 푼다.",
     ["0클릭", "없음", "제품 이해 ◎"]),
]

def render(items):
    out = ""
    for zid, nm, badge, cls, mk, desc, mt in items:
        b = ('<span class="rec">%s</span>' % badge if cls == "rec"
             else '<span class="no">%s</span>' % badge if cls == "no" else "")
        m = '<div class="mt2">'
        for i, t in enumerate(mt):
            k = "g" if ("◎" in t or "첫" in t or "눈에 띔" in t or "안 막음" in t
                        or t.startswith("0")) else                 ("r" if ("매번" in t or "△" in t or "안 띔" in t or "위험" in t
                         or "가림" in t) else "")
            head, _, tail = t.partition(" ")
            m += '<div class="%s"><b>%s</b>%s</div>' % (k, head, tail or "&nbsp;")
        m += '</div>'
        out += ('<div class="zc"><div class="zhd"><span class="zid">%s</span>'
                '<span class="znm">%s</span>%s</div><div class="zdesc">%s</div>%s%s</div>'
                % (zid, nm, b, desc, mk, m))
    return out


cards = render(OPTS)
pills = render(PILLS)

_unused = ""
for zid, nm, badge, cls, mk, desc, mt in []:
    b = ('<span class="rec">추천</span>' if cls == "rec"
         else '<span class="no">현행</span>' if cls == "no" else "")
    m = '<div class="mt2">'
    for i, t in enumerate(mt):
        k = "g" if (i == 0 and t.startswith("0")) or "◎" in t or "첫" in t else \
            ("r" if "매번" in t or "△" in t else "")
        head, _, tail = t.partition(" ")
        m += '<div class="%s"><b>%s</b>%s</div>' % (k, head, tail or "&nbsp;")
    m += '</div>'
    cards += ('<div class="zc"><div class="zhd"><span class="zid">%s</span>'
              '<span class="znm">%s</span>%s</div><div class="zdesc">%s</div>%s%s</div>'
              % (zid, nm, b, desc, mk, m))

hubtr = "".join('<tr><td class="k">%s</td><td class="num">%d건</td>'
                '<td class="num">%.0f%%</td><td>%s</td></tr>'
                % (h["name"], h["n"], 100.0 * h["n"] / N,
                   "<b style='color:#F2603F'>희소</b> — 10곳 미만" if h["n"] < SPARSE else "")
                for h in HUBS)

html = ("<!doctype html><html lang=ko><head><meta charset=utf-8>"
        "<meta name=viewport content='width=device-width,initial-scale=1'>"
        "<title>갈래말래 — 화면0</title><style>" + CSS + EXTRA +
        "</style></head><body><div class=wrapZ>"
        "<h1>화면0 &mdash; <em>출발지를 어떻게 고르나</em></h1>"
        "<p class=lede>현행(<code>discover.js:262~284</code>)은 <b>전체 화면 인트로</b>다. "
        "한국 지도에 핀 넷을 찍고 고르면 <code>#intro</code>가 숨는다. 실제 허브 딜 수로 그렸다.</p>"
        "<table><tr><th>허브</th><th style='text-align:right'>딜</th>"
        "<th style='text-align:right'>비중</th><th></th></tr>" + hubtr + "</table>"
        "<h2><span class=n>01</span>화면0을 둘까</h2>"
        "<div class=zrow>" + cards + "</div>"
        "<div class=callout><b>내가 Z2를 추천했다가 뒤집었다.</b><br>"
        "내 논리는 &lsquo;화면0이 제품을 설명한다&rsquo;였는데, "
        "<b>딜을 바로 보여주는 게 더 잘 설명한다.</b> "
        "<code>어디서 출발해요?</code>는 <b>아무 가치도 안 준 채 질문부터</b> 하고, "
        "<code>서울 &rarr; 제주 33,004원</code>은 그 자체로 설명이다.<br>"
        "첫 화면이 질문이면 <b>이탈 지점이 하나 는다.</b> 발견 서비스는 일단 보여줘야 한다.</div>"
        "<h2><span class=n>02</span>그럼 서울이 아닌 45%는 어떻게 바꾸나</h2>"
        "<p class=note>Z3의 유일한 위험은 <b>&lsquo;서울 전용 서비스&rsquo;로 읽히는 것</b>이다. "
        "부산 사람이 바꾸는 버튼을 못 찾으면 그대로 나간다. 헤더 처리를 셋으로 그렸다.</p>"
        "<div class=zrow>" + pills + "</div>"
        "<h2><span class=n>왜</span>P2 &mdash; 띄우되 막지 않는다</h2>"
        "<div class=callout><b>막는 대신 띄운다.</b><br>"
        "뒤에 <b>딜이 이미 보이는 채로</b> 한 줄 띠가 &lsquo;서울 출발로 보고 있어요&rsquo;라고 알린다. "
        "닫으면 다시 안 뜬다. <b>P3(드롭다운 열어둠)는 결국 작아진 화면0</b>이라 딜을 가린다.</div>"
        "<ul class=k>"
        "<li><b>알약을 코랄로 올린다.</b> 회색이면 &lsquo;장식&rsquo;으로 읽힌다. "
        "이건 <b>이 제품에서 두 번째로 중요한 조작</b>이다 &mdash; 첫째는 딜 고르기.</li>"
        "<li><b>드롭다운에 건수를 붙인다.</b> <code>제주 8곳</code>처럼 보이면 고르기 전에 안다. "
        "희소 허브(10곳 미만)는 미리 티를 낸다 &mdash; 필터 건수와 같은 원리다.</li>"
        "<li><b>고른 출발지는 기억한다.</b> 잘 안 바뀌는 값이라 매번 물을 이유가 없다. "
        "안내 띠도 <b>첫 방문에만</b> 뜬다.</li>"
        "<li><b>딥링크가 기본값을 이긴다.</b> <code>#PUS-DAD</code>로 들어오면 "
        "저장된 값도 서울 기본값도 무시하고 <b>부산</b>이다(§CH4 확정).</li>"
        "<li>⚠️ <b>&lsquo;서울 출발&rsquo;은 인천+김포다.</b> 알약이 &lsquo;서울&rsquo;이라 말하는데 "
        "실제로는 두 공항을 합친 가상 허브다(<code>SEL</code>). "
        "김포 딜을 보고 인천으로 갈까 헷갈릴 자리라 <b>확장 상세에서 공항을 밝힌다.</b></li>"
        "</ul>"
        "<p class=note>&#9888; <b>&lsquo;기억&rsquo;은 <code>localStorage</code>가 필요하다.</b> "
        "필터를 URL에 안 넣기로 한 것과는 다른 문제다 &mdash; 그건 "
        "<b>공유받은 사람에게 남의 필터를 강요하지 않으려는</b> 결정이었고, "
        "출발지 기억은 <b>내 기기에서 나만 겪는 편의</b>다. 공유 링크는 해시가 이기므로 충돌하지 않는다.</p>"
        "<p class=note>&#9888; 이 세션엔 브라우저가 없어 실제 렌더를 못 본다. "
        "특히 <b>뒤 배경 흐림(<code>backdrop-filter</code>)</b>이 저사양 기기에서 어떤지는 봐야 안다 &mdash; "
        "안 되면 <b>불투명 배경으로 폴백</b>한다.</p>"
        "<p class=foot>생성 <b>design/build_origin.py</b> &middot; 데이터 <b>docs/data/deals.json</b> "
        "&middot; 확정 홈 <b>home.html</b> &middot; 스펙 <b>../SPEC.md</b> &sect;CH2</p>"
        "</div></body></html>")

io.open(os.path.join(BASE, "origin.html"), "w", encoding="utf-8").write(html)
print("origin.html  %.1fKB" % (len(html) / 1024.0))
for h in HUBS:
    print("  %-4s %3d deals  %s" % (h["code"], h["n"], "SPARSE" if h["n"] < SPARSE else ""))
