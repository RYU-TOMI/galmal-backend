# -*- coding: utf-8 -*-
"""모바일 — 세로 화면에서 지도와 카드를 어떻게 나누나.

현행(discover.css @media max-width:860px)은 지도 56% + 가로 스크롤 카드다.
390x740 뷰포트에 실제 딜로 그린다.
소유: 기획 세션. 산출물 design/mobile.html
"""
import json, io, os, sys

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
from _app import CSS
from _fmt import tier, direct, card_tags, money, daterange, datesub

D = json.load(io.open(os.path.join(BASE, "..", "docs", "data", "deals.json"), encoding="utf-8"))
SEL = sorted([d for d in D["deals"] if d["o"] == "SEL"], key=lambda x: x["price"])
N = len(SEL)

VW, VH = 390, 740
HDR = 46
BAR = 52          # 검색 + 알약
CARD_H = 103      # 확정 카드 높이(태그 없음)
GAP = 9
SORT_H = 40

USABLE = VH - HDR

EXTRA = """
.wrapM{max-width:1180px;margin:0 auto;padding:44px 26px 90px}
.mrow{display:flex;gap:22px;flex-wrap:wrap;align-items:flex-start;margin:16px 0 34px}
.mc{width:390px}
.mhd{display:flex;align-items:baseline;gap:8px}
.mid{font-size:.64rem;font-weight:900;background:var(--ink);color:#fff;border-radius:4px;padding:2px 7px}
.mnm{font-weight:800;font-size:.9rem}
.rec{font-size:.55rem;font-weight:900;background:var(--accent);color:#fff;border-radius:4px;padding:2px 6px;vertical-align:2px}
.no{font-size:.55rem;font-weight:900;background:var(--sub);color:#fff;border-radius:4px;padding:2px 6px;vertical-align:2px}
.mdesc{color:var(--sub);font-size:.77rem;line-height:1.6;min-height:70px;margin:5px 0 10px}
.vp{width:390px;height:740px;border:1px solid #cfdad7;border-radius:22px;overflow:hidden;
 position:relative;background:var(--sea)}
.mh{height:46px;background:#fff;border-bottom:1px solid var(--line);display:flex;
 align-items:center;padding:0 13px;gap:10px;position:relative;z-index:8}
.mlogo{font-weight:900;font-size:.92rem;letter-spacing:-.03em}
.mlogo i{font-style:normal;color:var(--accent)}
.mpill{margin-left:auto;background:#fff;border:1.5px solid var(--accent);color:var(--accent);
 border-radius:99px;padding:4px 12px;font-size:.74rem;font-weight:900}
.mmap{position:absolute;left:0;right:0;background:
 radial-gradient(120px 90px at 24% 22%,var(--land),transparent 70%),
 radial-gradient(96px 70px at 70% 40%,var(--land),transparent 70%),
 radial-gradient(80px 60px at 40% 62%,var(--land),transparent 70%),var(--sea)}
.mpin{position:absolute;width:9px;height:9px;margin:-4.5px 0 0 -4.5px;border-radius:99px;
 background:var(--accent);box-shadow:0 0 0 3px rgba(242,96,63,.18)}
.mbar{position:absolute;left:10px;right:10px;height:44px;background:#fff;border:1px solid var(--line);
 border-radius:11px;display:flex;align-items:center;gap:7px;padding:0 11px;z-index:7;
 box-shadow:0 3px 12px rgba(20,50,45,.1)}
.mmag{color:var(--sub);font-size:.84rem}
.mph{font-size:.76rem;color:var(--sub);font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.msep{width:1px;height:20px;background:var(--line);flex:none}
.mfb{background:var(--soft);border:1px solid var(--line);border-radius:99px;padding:3px 9px;
 font-size:.66rem;font-weight:800;color:var(--sub);white-space:nowrap;flex:none}
.mstage{position:absolute;left:10px;display:flex;gap:5px;z-index:7}
.mspill{background:#fff;border:1px solid var(--line);border-radius:99px;padding:5px 11px;
 font-size:.68rem;font-weight:800;color:var(--sub);box-shadow:0 2px 8px #0000000f;white-space:nowrap}
.mspill.on{background:var(--ink);color:#fff;border-color:var(--ink)}
/* 시트 */
.msheet{position:absolute;left:0;right:0;bottom:0;background:var(--sea);
 border-radius:18px 18px 0 0;box-shadow:0 -10px 28px rgba(16,44,38,.18);
 border-top:1px solid var(--line);z-index:6;overflow:hidden}
.mgrab{width:38px;height:4px;border-radius:99px;background:#c3cfcc;margin:9px auto 6px}
.msort{display:flex;gap:5px;padding:0 10px 8px}
.mspl{background:#fff;border:1px solid var(--line);border-radius:99px;padding:4px 10px;
 font-size:.64rem;font-weight:800;color:var(--sub)}
.mspl.on{background:var(--ink);color:#fff;border-color:var(--ink)}
.mfeed{display:flex;flex-direction:column;gap:9px;padding:0 10px}
/* 가로 스크롤(현행) */
.hfeed{position:absolute;left:0;right:0;bottom:0;background:var(--sea);border-top:1px solid var(--line);
 display:flex;gap:9px;padding:10px;overflow:hidden;z-index:6}
.hcard{flex:0 0 208px;background:#fff;border:1.5px solid var(--line);border-radius:13px;padding:10px}
.hcard .ph{width:100%;height:96px;border-radius:9px;margin-bottom:8px;
 background:linear-gradient(140deg,#cfe0dc,#e9efed)}
/* 카드 */
.fcard{display:flex;gap:11px;background:#fff;border:1.5px solid var(--line);
 border-radius:13px;padding:10px}
.thumb{flex:none;width:62px;height:62px;border-radius:10px;
 background:linear-gradient(140deg,#cfe0dc,#e9efed)}
.fbody{flex:1;min-width:0}
.frow{display:flex;justify-content:space-between;align-items:center;gap:6px}
.fcity{font-size:.98rem;font-weight:900;letter-spacing:-.02em;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.prow{display:flex;justify-content:space-between;align-items:center;gap:8px;margin-top:2px}
.price{font-weight:900;font-size:1.14rem;letter-spacing:-.03em;font-variant-numeric:tabular-nums}
.price small{font-size:.6em;font-weight:700;color:var(--sub);margin-left:2px}
.dmain{font-size:.74rem;margin-top:5px}
.dsub{font-size:.63rem;margin-top:2px}
.bdg{font-size:.58rem;font-weight:800;border-radius:99px;padding:2px 8px;flex:none;
 background:var(--coast);color:#fff;white-space:nowrap}
.stamp{flex:none;font-weight:900;white-space:nowrap;border-radius:4px}
.stamp.t1{transform:rotate(-7deg);border:1.5px solid var(--accent);color:var(--accent);
 font-size:.52rem;padding:1px 5px;background:#fff}
.stamp.t2{transform:rotate(-8deg);background:var(--accent);color:#fff;font-size:.58rem;padding:2px 7px}
.stamp.t3{transform:rotate(-9deg);background:linear-gradient(135deg,#F2603F,#FF8A63 42%,#C6472A);
 color:#fff;font-size:.6rem;padding:2px 8px;box-shadow:0 0 0 2px #fff}
.tabs{position:absolute;left:0;right:0;top:46px;height:40px;background:#fff;
 border-bottom:1px solid var(--line);display:flex;z-index:7}
.tab{flex:1;display:flex;align-items:center;justify-content:center;font-size:.8rem;
 font-weight:800;color:var(--sub)}
.tab.on{color:var(--ink);box-shadow:inset 0 -2px 0 var(--accent)}
.mt3{display:flex;gap:7px;margin-top:9px}
.mt3 div{flex:1;background:#fff;border:1px solid var(--line);border-radius:9px;padding:7px 8px;
 text-align:center;font-size:.62rem;color:var(--sub);font-weight:700;line-height:1.4}
.mt3 b{display:block;font-size:1.0rem;letter-spacing:-.02em;color:var(--ink)}
.mt3 .g b{color:#1E7A50}.mt3 .r b{color:var(--accent)}
.steps{display:flex;gap:9px;margin:10px 0 0;flex-wrap:wrap}
.step{flex:1;min-width:110px;background:#fff;border:1px solid var(--line);border-radius:10px;
 padding:8px 9px;font-size:.68rem;line-height:1.5;color:var(--sub);font-weight:700}
.step b{display:block;color:var(--ink);font-size:.76rem;margin-bottom:2px}
"""

PINS = "".join('<span class="mpin" style="left:%d%%;top:%d%%"></span>' % g
               for g in [(22, 20), (40, 14), (58, 34), (30, 50), (70, 56), (46, 68),
                         (76, 26), (34, 78), (62, 84)])


def card(d):
    t = tier(d)
    stamp = ('<span class="stamp %s">%d%%&darr;</span>' % (t, d["discount"])) if t else ""
    bdg = '<span class="bdg">&#9992; 직항</span>' if direct(d) else ""
    return ('<div class="fcard"><div class="thumb"></div><div class="fbody">'
            '<div class="frow"><span class="fcity">%s</span>%s</div>'
            '<div class="prow"><span class="price">%s<small>원</small></span>%s</div>'
            '<div class="dmain">%s</div><div class="dsub">%s</div></div></div>'
            % (d["ko"], stamp, money(d["price"]), bdg,
               daterange(d.get("dep"), d.get("ret")), datesub(d)))


def hcard(d):
    t = tier(d)
    stamp = ('<span class="stamp %s">%d%%&darr;</span>' % (t, d["discount"])) if t else ""
    return ('<div class="hcard"><div class="ph"></div>'
            '<div class="frow"><span class="fcity">%s</span>%s</div>'
            '<div class="prow"><span class="price">%s<small>원</small></span></div>'
            '<div class="dmain">%s</div></div>'
            % (d["ko"], stamp, money(d["price"]),
               daterange(d.get("dep"), d.get("ret"))))


HEAD = ('<div class="mh"><span class="mlogo">갈래<i>말래</i></span>'
        '<span class="mpill">서울 출발 &#9662;</span></div>')
SEARCH = ('<span class="mmag">&#9906;</span><span class="mph">어디로 갈까요?</span>'
          '<span class="msep"></span><span class="mfb">아무때</span>'
          '<span class="mfb">예산</span>')
STAGEBAR = ('<span class="mspill">가까운 곳</span><span class="mspill on">조금 더 멀리</span>'
            '<span class="mspill">아주 멀리</span>')


def sheet(h, cards_n, show_sort=True):
    inner = '<div class="mgrab"></div>'
    if show_sort:
        inner += ('<div class="msort"><span class="mspl on">가성비순</span>'
                  '<span class="mspl">임박순</span><span class="mspl">할인율순</span></div>')
    inner += '<div class="mfeed">' + "".join(card(d) for d in SEL[:cards_n]) + '</div>'
    return '<div class="msheet" style="height:%dpx">%s</div>' % (h, inner)


def viewport(inner):
    return '<div class="vp">' + inner + '</div>'


# ── N0 현행: 지도 56% + 가로 스크롤 ────────────────────────────
map_h0 = int(USABLE * 0.56)
feed_h0 = USABLE - map_h0
N0 = viewport(HEAD
              + '<div class="mmap" style="top:46px;height:%dpx">%s</div>' % (map_h0, PINS)
              + '<div class="mbar" style="top:%dpx">%s</div>' % (46 + 10, SEARCH)
              + '<div class="mstage" style="top:%dpx">%s</div>' % (46 + map_h0 - 40, STAGEBAR)
              + '<div class="hfeed" style="height:%dpx">%s</div>'
              % (feed_h0, "".join(hcard(d) for d in SEL[:3])))

# ── N1 3단 시트 (half 상태) ────────────────────────────────────
SHEET_HALF = 340
N1 = viewport(HEAD
              + '<div class="mmap" style="top:46px;bottom:0">%s</div>' % PINS
              + '<div class="mbar" style="top:%dpx">%s</div>' % (46 + 10, SEARCH)
              + '<div class="mstage" style="bottom:%dpx">%s</div>' % (SHEET_HALF + 10, STAGEBAR)
              + sheet(SHEET_HALF, 4))

# ── N2 탭 전환 (목록 탭) ───────────────────────────────────────
N2 = viewport(HEAD
              + '<div class="tabs"><span class="tab">지도</span>'
                '<span class="tab on">목록</span></div>'
              + '<div style="position:absolute;left:0;right:0;top:86px;bottom:0;'
                'background:var(--sea);padding:10px">'
                '<div class="mbar" style="position:static;margin-bottom:9px">%s</div>'
                '<div class="mfeed" style="padding:0">%s</div></div>'
              % (SEARCH, "".join(card(d) for d in SEL[:5])))

# ── N3 지도 고정 40% + 세로 리스트 ─────────────────────────────
map_h3 = int(USABLE * 0.40)
N3 = viewport(HEAD
              + '<div class="mmap" style="top:46px;height:%dpx">%s</div>' % (map_h3, PINS)
              + '<div class="mbar" style="top:%dpx">%s</div>' % (46 + 10, SEARCH)
              + '<div class="mstage" style="top:%dpx">%s</div>' % (46 + map_h3 - 40, STAGEBAR)
              + '<div class="msheet" style="height:%dpx;border-radius:0">'
                '<div class="msort" style="padding-top:9px">'
                '<span class="mspl on">가성비순</span><span class="mspl">임박순</span></div>'
                '<div class="mfeed">%s</div></div>'
              % (USABLE - map_h3, "".join(card(d) for d in SEL[:4])))


def n_cards(feed_px, sort=True):
    avail = feed_px - (SORT_H if sort else 0) - 15
    return max(0, avail + GAP) / float(CARD_H + GAP)


OPTS = [
    ("N0", "지도 56% + 가로 스크롤", "현행", "no", N0,
     "카드가 <b>가로로</b> 흐른다. 390px에 <b>208px 카드</b>라 "
     "<b>1.8장</b>밖에 안 보인다 &mdash; <b>비교가 안 된다.</b><br>"
     "가로 스크롤은 <b>훑기도 어렵다</b>. 세로로 읽는 화면에서 손가락 방향이 바뀐다.",
     ["%.1f장" % (VW / float(208 + GAP)), "%dpx" % map_h0, "고정"]),
    ("N1", "지도 배경 + 3단 시트", "추천", "rec", N1,
     "지도가 <b>화면 전체</b>를 채우고 카드 시트가 위로 올라온다. "
     "<b>peek / half / full</b> 세 높이를 <b>사용자가 끌어서</b> 정한다.<br>"
     "우리가 비중을 못 정하는 게 아니라 <b>상황마다 다르다</b> &mdash; 훑을 땐 넓히고, "
     "지도를 볼 땐 내린다.",
     ["%.1f장" % n_cards(SHEET_HALF), "가변", "사용자"]),
    ("N2", "탭 전환", "", "", N2,
     "<code>지도</code>와 <code>목록</code>을 탭으로 가른다. 각각 <b>전체 화면</b>을 쓴다.<br>"
     "가장 많이 보이지만 <b>둘을 동시에 못 본다</b> &mdash; "
     "지도에서 핀을 누르고 카드를 보려면 탭을 옮겨야 한다.",
     ["%.1f장" % n_cards(USABLE - 40 - 44), "전체(탭)", "고정"]),
    ("N3", "지도 40% 고정 + 세로 리스트", "", "", N3,
     "가로를 세로로 바꾸기만 했다. <b>현행보다 두 배 가까이 보인다.</b><br>"
     "단순하고 예측 가능하지만 <b>비중이 고정</b>이라 지도를 크게 볼 수 없다.",
     ["%.1f장" % n_cards(USABLE - map_h3), "%dpx" % map_h3, "고정"]),
]

cards_html = ""
for mid, nm, badge, cls, mk, desc, mt in OPTS:
    b = ('<span class="rec">%s</span>' % badge if cls == "rec"
         else '<span class="no">%s</span>' % badge if cls == "no" else "")
    m = '<div class="mt3">'
    for i, t in enumerate(mt):
        k = "g" if (i == 0 and float(t.replace("장", "") or 0) >= 2.5) or t in ("가변", "사용자") \
            else ("r" if t == "고정" and i == 2 else "")
        m += '<div class="%s"><b>%s</b>%s</div>' % (
            k, t, ["보이는 카드", "지도", "비중"][i])
    m += '</div>'
    cards_html += ('<div class="mc"><div class="mhd"><span class="mid">%s</span>'
                   '<span class="mnm">%s</span>%s</div><div class="mdesc">%s</div>%s%s</div>'
                   % (mid, nm, b, desc, mk, m))

STEPS = ('<div class="steps">'
         '<div class="step"><b>peek &mdash; 160px</b>카드 1장. 지도가 최대로 보인다. '
         '핀을 누르거나 지도를 볼 때</div>'
         '<div class="step"><b>half &mdash; 340px</b>카드 %.1f장. 기본값. '
         '지도와 목록을 같이 본다</div>'
         '<div class="step"><b>full &mdash; 화면 대부분</b>카드 %.1f장. '
         '훑고 비교할 때. 지도는 위에 살짝</div>'
         '</div>' % (n_cards(340), n_cards(USABLE - 60)))

html = ("<!doctype html><html lang=ko><head><meta charset=utf-8>"
        "<meta name=viewport content='width=device-width,initial-scale=1'>"
        "<title>갈래말래 — 모바일</title><style>" + CSS + EXTRA +
        "</style></head><body><div class=wrapM>"
        "<h1>모바일 &mdash; <em>지도와 카드를 어떻게 나누나</em></h1>"
        "<p class=lede><b>390&times;740</b> 뷰포트에 서울 출발 실제 딜로 그렸다. "
        "데스크톱은 <b>좌우</b>로 나눴지만 모바일은 <b>위아래</b>라 저울이 통째로 다르다 &mdash; "
        "패널 폭에서 얻은 결론이 여기선 안 통한다.</p>"
        "<div class=callout><b>현행의 진짜 문제는 비중이 아니라 방향이다.</b><br>"
        "지도 56%는 나쁘지 않은데, 카드가 <b>가로로</b> 흘러서 <b>1.8장</b>밖에 안 보인다. "
        "발견 서비스에서 <b>비교가 안 되는</b> 게 치명적이고, "
        "세로로 읽는 화면에서 <b>손가락 방향이 바뀌는</b> 것도 부담이다.</div>"
        "<div class=mrow>" + cards_html + "</div>"
        "<h2><span class=n>N1</span>세 높이</h2>"
        "<p class=note>위 그림은 <b>half</b> 상태다. 손잡이를 끌어 셋 사이를 오간다.</p>"
        + STEPS +
        "<h2><span class=n>왜</span>N1</h2>"
        "<ul class=k>"
        "<li><b>비중을 우리가 정할 문제가 아니다.</b> 지도를 볼 때와 목록을 훑을 때 "
        "필요한 비중이 다르다. <b>고정하면 둘 중 하나는 늘 답답하다</b>(N0·N3).</li>"
        "<li><b>지도가 배경으로 살아 있다.</b> 탭(N2)은 카드를 가장 많이 보여주지만 "
        "<b>지도와 목록이 서로를 못 본다</b> &mdash; 핀을 누르고 카드를 보려면 탭을 옮겨야 한다. "
        "지도가 본체인 제품에서 그 단절은 크다.</li>"
        "<li><b>상세와 같은 은유다.</b> 확장 상세도 하단 시트로 확정했다(§CH4). "
        "카드를 누르면 <b>같은 시트 안에서 상세로 밀려 들어가고</b> 뒤로가기로 돌아온다 &mdash; "
        "<b>시트 두 장이 겹치지 않는다.</b></li>"
        "<li><b>단계바는 시트 바로 위에 띄운다.</b> 지도 조작이라 지도 가까이 두되, "
        "<b>엄지가 닿는 아래쪽</b>이어야 한다. 검색 바는 위에 둔다 &mdash; 자주 안 쓰고, "
        "누르면 <b>전체 화면 검색</b>으로 열리므로 위치가 덜 중요하다.</li>"
        "<li>⚠️ <b>드래그가 세 군데서 부딪힌다</b> &mdash; 시트 높이 조절, 시트 안 스크롤, "
        "그리고 <b>예산 슬라이더</b>(§CH3). 슬라이더를 잡는 동안 시트 드래그를 막기로 한 것과 "
        "같은 처리가 필요하다.</li>"
        "</ul>"
        "<p class=note>&#9888; <b>지도는 자유 줌·팬이 없다</b>(§CH1 확정)는 게 여기서 도움이 된다. "
        "지도에 드래그 제스처가 없으므로 <b>시트 끌기와 안 부딪힌다.</b> "
        "자유 줌을 넣었다면 이 설계가 성립하지 않았다.</p>"
        "<p class=note>&#9888; 이 세션엔 브라우저가 없어 실제 렌더를 못 본다. "
        "특히 <b>시트 드래그 감각</b>은 손으로 만져봐야 안다.</p>"
        "<p class=foot>생성 <b>design/build_mobile.py</b> &middot; 데이터 <b>docs/data/deals.json</b>"
        "(서울 " + str(N) + "건) &middot; 확정 홈 <b>home.html</b> &middot; 스펙 <b>../SPEC.md</b></p>"
        "</div></body></html>")

io.open(os.path.join(BASE, "mobile.html"), "w", encoding="utf-8").write(html)
print("mobile.html  %.1fKB" % (len(html) / 1024.0))
print("  N0 현행 가로: %.1f장 · 지도 %dpx" % (VW / float(208 + GAP), map_h0))
print("  N1 half: %.1f장 · full: %.1f장 · peek: %.1f장"
      % (n_cards(340), n_cards(USABLE - 60), n_cards(160)))
print("  N2 탭: %.1f장 · N3: %.1f장" % (n_cards(USABLE - 40 - 44), n_cards(USABLE - map_h3)))
