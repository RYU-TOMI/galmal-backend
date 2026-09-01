# -*- coding: utf-8 -*-
"""검색 바(G2) 상태 설계 — 채택 확정(2026-09-01).

내가 반대한 이유는 "무엇을 칠지 모르는 사람"이었다. 그건 **눌렀을 때 어휘가 다 보이면**
사라진다 — 아는 사람은 치고, 모르는 사람은 눌러서 고른다.
그리고 검색이면 **도시 이름도 같이** 찾을 수 있다. 그게 진짜 이득이다.

실제 deals.json으로 그린다. 소유: 기획 세션. 산출물 design/search.html
"""
import json, io, os, sys, collections

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
from _app import CSS, MOODS_N
from _fmt import TOP, SUB, money, tier

D = json.load(io.open(os.path.join(BASE, "..", "docs", "data", "deals.json"), encoding="utf-8"))
deals = D["deals"]
SEL = sorted([d for d in deals if d["o"] == "SEL"], key=lambda x: x["price"])

# 어휘별 딜 수 (서울 기준)
tagn = collections.Counter(t for d in SEL for t in d["tags"])
# 도시 검색 예시
def city(ko):
    return next((d for d in SEL if d["ko"] == ko), None)

BAR_W = 788

EXTRA = """
.wrapS{max-width:1000px;margin:0 auto;padding:44px 26px 90px}
.state{margin:0 0 46px}
.slab{display:flex;align-items:baseline;gap:9px;margin-bottom:9px}
.sid{font-size:.66rem;font-weight:900;background:var(--ink);color:#fff;border-radius:4px;padding:2px 8px}
.snm{font-weight:800;font-size:.95rem}
.sdesc{color:var(--sub);font-size:.82rem;line-height:1.65;margin:0 0 12px;max-width:800px}
.hold{background:var(--sea);border:1px solid #cfdad7;border-radius:14px;padding:18px;position:relative}
.sbar{background:#fff;border:1px solid var(--line);border-radius:12px;height:52px;
 display:flex;align-items:center;gap:8px;padding:0 12px;box-shadow:0 4px 14px rgba(20,50,45,.08)}
.sbar.focus{border-color:var(--accent);box-shadow:0 0 0 3px rgba(242,96,63,.14)}
.sfield{flex:1;display:flex;align-items:center;gap:7px;min-width:0}
.mag{color:var(--sub);font-size:.9rem;flex:none}
.ph{font-size:.82rem;color:var(--sub);font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.typed{font-size:.82rem;font-weight:700;color:var(--ink)}
.cur{width:1.5px;height:16px;background:var(--accent);flex:none}
.tok{background:var(--accent);color:#fff;border-radius:6px;padding:3px 9px;
 font-size:.72rem;font-weight:800;white-space:nowrap;flex:none}
.tok .x{opacity:.72;margin-left:5px}
.tok.sub{background:var(--coast)}
.vsep{width:1px;height:22px;background:var(--line);flex:none}
.spill2{background:var(--soft);border:1px solid var(--line);border-radius:99px;padding:5px 12px;
 font-size:.72rem;font-weight:800;color:var(--sub);white-space:nowrap;flex:none}
.cnt{font-size:.72rem;font-weight:800;color:var(--sub);white-space:nowrap;flex:none;margin-left:2px}
/* 드롭다운 */
.dd{margin-top:8px;background:#fff;border:1px solid var(--line);border-radius:12px;
 padding:11px 12px;box-shadow:0 10px 30px rgba(16,44,38,.16)}
.ddg{font-size:.62rem;font-weight:800;color:var(--sub);margin:9px 2px 6px;
 display:flex;align-items:center;gap:7px}
.ddg:first-child{margin-top:2px}
.ddg .line{flex:1;height:1px;background:var(--line)}
.ddrow{display:flex;align-items:center;gap:9px;padding:7px 8px;border-radius:8px;font-size:.8rem}
.ddrow.on{background:#FFF4F1}
.ddrow .nm{font-weight:800}
.ddrow .mt{color:var(--sub);font-size:.72rem;font-weight:700}
.ddrow .rt{margin-left:auto;font-size:.74rem;color:var(--sub);font-weight:700;
 font-variant-numeric:tabular-nums;white-space:nowrap}
.ddrow .rt b{color:var(--accent);font-weight:900}
.ddchips{display:flex;gap:5px;flex-wrap:wrap;padding:2px 2px 4px}
.ddchip{background:var(--soft);border:1px solid var(--line);border-radius:99px;
 padding:4px 11px;font-size:.74rem;font-weight:800;color:var(--ink)}
.ddchip .n{color:var(--sub);font-weight:700;margin-left:5px;font-size:.68rem}
.ddchip.on{background:var(--accent);color:#fff;border-color:var(--accent)}
.ddchip.on .n{color:#fff9}
.empty{padding:14px 8px;text-align:center}
.empty .big{font-size:.86rem;font-weight:800;margin-bottom:5px}
.empty .sml{font-size:.76rem;color:var(--sub);line-height:1.6}
.kbd{font-family:ui-monospace,Consolas,monospace;font-size:.72rem;background:var(--soft);
 border:1px solid var(--line);border-radius:5px;padding:1px 6px;font-weight:700}
"""

def bar(inner, focus=False):
    return '<div class="sbar%s">%s</div>' % (" focus" if focus else "", inner)


RIGHT = ('<span class="vsep"></span>'
         '<span class="spill2">아무때 &#9662;</span>'
         '<span class="spill2">100만 이하 &#9662;</span>'
         '<span class="cnt">%d곳</span>' % len(SEL))

# ── S1 평소 ────────────────────────────────────────────────────
s1 = bar('<span class="sfield"><span class="mag">&#9906;</span>'
         '<span class="ph">어디로 갈까요? &nbsp;해변 · 야경 · 온천 · 다낭&hellip;</span></span>' + RIGHT)

# ── S2 눌렀을 때 (아무것도 안 침) ──────────────────────────────
top_chips = "".join('<span class="ddchip">%s<span class="n">%d</span></span>' % (t, tagn.get(t, 0))
                    for t in TOP)
sub_show = [t for t in ["야경", "리조트", "골목", "유적", "야시장", "쇼핑", "사원", "트레킹"]
            if tagn.get(t)]
sub_chips = "".join('<span class="ddchip">%s<span class="n">%d</span></span>' % (t, tagn.get(t, 0))
                    for t in sub_show)
recent = SEL[0]
s2 = (bar('<span class="sfield"><span class="mag">&#9906;</span><span class="cur"></span>'
          '<span class="ph">어디로 갈까요?</span></span>' + RIGHT, focus=True)
      + '<div class="dd">'
        '<div class="ddg">분위기<span class="line"></span></div>'
        '<div class="ddchips">' + top_chips + '</div>'
        '<div class="ddg">이런 것도<span class="line"></span></div>'
        '<div class="ddchips">' + sub_chips + '</div>'
        '<div class="ddg">오늘의 발견<span class="line"></span></div>'
        '<div class="ddrow"><span class="nm">%s</span>'
        '<span class="mt">%s</span><span class="rt"><b>%s원</b></span></div>'
        '</div>' % (recent["ko"], recent["country"], money(recent["price"])))

# ── S3 타이핑 중 — 분위기와 도시가 같이 나온다 ─────────────────
q = "사"   # 태그(사막·사원)와 도시(사이판)가 같이 걸리는 실제 예시
hit_tags = [t for t in list(TOP) + sorted(SUB) if t.startswith(q) and tagn.get(t)]
hit_city = [d for d in SEL if d["ko"].startswith(q)][:3]
rows = ""
if hit_tags:
    rows += '<div class="ddg">분위기<span class="line"></span></div><div class="ddchips">'
    rows += "".join('<span class="ddchip">%s<span class="n">%d</span></span>' % (t, tagn[t]) for t in hit_tags)
    rows += '</div>'
rows += '<div class="ddg">목적지<span class="line"></span></div>'
for i, d in enumerate(hit_city):
    rows += ('<div class="ddrow%s"><span class="nm">%s</span><span class="mt">%s</span>'
             '<span class="rt"><b>%s원</b> &middot; %s</span></div>'
             % (" on" if i == 0 else "", d["ko"], d["country"], money(d["price"]), d["when"]))
s3 = (bar('<span class="sfield"><span class="mag">&#9906;</span>'
          '<span class="typed">%s</span><span class="cur"></span></span>' % q + RIGHT, focus=True)
      + '<div class="dd">' + rows + '</div>')

# ── S4 고른 뒤 ─────────────────────────────────────────────────
n_filt = sum(1 for d in SEL if "문화" in d["tags"] and "유적" in d["tags"]) or \
         sum(1 for d in SEL if "문화" in d["tags"])
s4 = bar('<span class="sfield"><span class="mag">&#9906;</span>'
         '<span class="tok">문화<span class="x">&times;</span></span>'
         '<span class="tok sub">유적<span class="x">&times;</span></span>'
         '<span class="cur"></span></span>'
         '<span class="vsep"></span>'
         '<span class="spill2">이번 달 &#9662;</span>'
         '<span class="spill2">100만 이하 &#9662;</span>'
         '<span class="cnt">%d곳</span>' % n_filt)

# ── S5 결과 없음 ───────────────────────────────────────────────
# 서울엔 없는데 다른 허브엔 있는 실제 도시를 고른다 — F5 경로를 진짜로 보여준다
_selc = {d["ko"] for d in SEL}
_cand = sorted({d["ko"] for d in deals if d["o"] != "SEL" and d["ko"] not in _selc})
miss = _cand[0] if _cand else "광저우"
alt = sorted([d for d in deals if d["ko"] == miss], key=lambda x: x["price"])
altmsg = ("<b>%s 출발</b>이면 오늘 있어요 &mdash; <b>%s원</b>"
          % (D["origins"][alt[0]["o"]]["name"], money(alt[0]["price"]))) if alt else \
         "오늘은 어느 출발지에도 없어요. 다른 분위기를 골라볼까요?"
s5 = (bar('<span class="sfield"><span class="mag">&#9906;</span>'
          '<span class="typed">%s</span><span class="cur"></span></span>' % miss + RIGHT, focus=True)
      + '<div class="dd"><div class="empty">'
        '<div class="big">서울 출발 %s 딜은 오늘 없어요</div>'
        '<div class="sml">%s</div></div></div>' % (miss, altmsg))

STATES = [
    ("S1", "평소",
     "한 줄이고 <b>52px</b>이다. 플레이스홀더가 <b>무엇을 칠 수 있는지</b> 보여준다 &mdash; "
     "분위기와 도시 이름을 <b>같이</b> 예로 든다. 날짜·예산은 오른쪽 알약으로 남긴다.", s1),
    ("S2", "눌렀을 때 &mdash; 타이핑 없이도 다 보인다",
     "🔑 <b>이게 검색을 채택할 수 있게 만드는 부분이다.</b> 검색창은 원래 "
     "&lsquo;무엇을 찾을지 아는 사람&rsquo;의 도구인데, 우리 사용자는 그걸 모르는 채로 온다.<br>"
     "<b>누르기만 하면 어휘가 다 펼쳐지므로</b> 모르는 사람은 고르고 아는 사람은 친다. "
     "현행 도크가 늘 보여주던 걸 <b>필요할 때만</b> 보여주는 셈이라 잃는 게 없다.", s2),
    ("S3", "치는 중 &mdash; 분위기와 목적지가 같이",
     "<b>&lsquo;사&rsquo; 한 글자에 분위기와 도시가 함께 걸린다</b>(사막·사원 · 사이판). 결과를 <b>두 무리로 갈라</b> "
     "무엇을 고르는지 헷갈리지 않게 한다.<br>"
     "<b>분위기는 필터, 목적지는 이동</b>이다 &mdash; 다른 동작이라 자리를 나눴다.", s3),
    ("S4", "고른 뒤",
     "고른 건 입력창 안에 <b>토큰</b>으로 남는다. 상위 어휘는 코랄, 하위 어휘는 청록이라 "
     "<b>어느 층인지</b>가 색으로 보인다. 오른쪽 <b>결과 수</b>가 필터가 한 일을 말해준다.", s4),
    ("S5", "없을 때",
     "<b>빈손으로 돌려보내지 않는다.</b> 다른 출발지에 그 도시가 있으면 알려준다 &mdash; "
     "<code>FLOWS.md</code> <b>F5</b>와 같은 처리다.", s5),
]

secs = ""
for sid, nm, desc, mk in STATES:
    secs += ('<div class="state"><div class="slab"><span class="sid">%s</span>'
             '<span class="snm">%s</span></div><p class="sdesc">%s</p>'
             '<div class="hold">%s</div></div>' % (sid, nm, desc, mk))

html = ("<!doctype html><html lang=ko><head><meta charset=utf-8>"
        "<meta name=viewport content='width=device-width,initial-scale=1'>"
        "<title>갈래말래 — 검색 바</title><style>" + CSS + EXTRA +
        "</style></head><body><div class=wrapS>"
        "<h1>검색 바 &mdash; <em>다섯 가지 상태</em></h1>"
        "<p class=lede><b>G2 채택 확정</b>(2026-09-01). 아래 바 하나로 분위기와 목적지를 같이 찾는다. "
        "서울 출발 " + str(len(SEL)) + "건 실데이터로 그렸다.</p>"
        "<div class=callout><b>내가 반대했던 이유는 설계로 풀린다.</b><br>"
        "&ldquo;검색창은 무엇을 찾을지 아는 사람의 도구인데 우리 사용자는 모르는 채로 온다&rdquo;고 했는데, "
        "<b>누르면 어휘가 다 펼쳐지게</b> 하면 그 문제가 사라진다(S2). "
        "모르는 사람은 <b>고르고</b>, 아는 사람은 <b>친다</b>.<br>"
        "그리고 검색이라서 <b>도시 이름을 같이 찾을 수 있다</b> &mdash; "
        "&lsquo;다낭 얼마지?&rsquo;라고 오는 사람이 지금은 갈 데가 없었다.</div>"
        + secs +
        "<h2><span class=n>규칙</span>정한 것</h2>"
        "<table><tr><th style='width:190px'>무엇을</th><th>어떻게</th></tr>"
        "<tr><td class=k>검색 대상</td><td><b>상위 어휘 6</b> + <b>하위 어휘 18</b> + "
        "<b>도시 이름</b>. 나라 이름은 넣지 않는다 &mdash; "
        "&lsquo;일본&rsquo;을 치면 결과가 너무 넓어 고르는 재미가 사라진다</td></tr>"
        "<tr><td class=k><b>분위기 vs 목적지</b></td><td><b>분위기는 필터</b>(누르면 토큰이 되고 피드가 줄어든다), "
        "<b>목적지는 이동</b>(누르면 그 딜의 상세가 열린다 &mdash; 지도가 스르륵 움직이는 그 동작 그대로). "
        "<b>동작이 다르므로 결과를 두 무리로 가른다</b></td></tr>"
        "<tr><td class=k>토큰 색</td><td>상위는 <b>코랄</b>, 하위는 <b>청록</b>. "
        "<code>문화</code>와 <code>유적</code>이 같은 층이 아님을 색으로 보인다</td></tr>"
        "<tr><td class=k>여러 개 고르기</td><td><b>AND</b>다 &mdash; <code>문화</code>+<code>유적</code>은 둘 다 가진 곳. "
        "결과 수가 옆에 있어 <b>0곳이 되는 걸 즉시 안다</b></td></tr>"
        "<tr><td class=k>날짜·예산</td><td>검색창에 <b>안 넣는다.</b> 값이 <b>범위</b>라 타이핑으로 고르기 나쁘다. "
        "오른쪽 알약 + 팝오버로 남긴다</td></tr>"
        "<tr><td class=k>결과 없음</td><td>다른 출발지에 그 도시가 있으면 <b>제안한다</b>(F5). "
        "없으면 다른 분위기를 권한다</td></tr>"
        "<tr><td class=k>키보드</td><td><span class=kbd>&darr;</span><span class=kbd>&uarr;</span> 이동 · "
        "<span class=kbd>Enter</span> 선택 · <span class=kbd>Esc</span> 닫기 · "
        "<span class=kbd>Backspace</span>는 빈 칸에서 <b>마지막 토큰을 지운다</b></td></tr>"
        "<tr><td class=k>모바일</td><td>바를 누르면 <b>전체 화면 검색</b>으로 올라온다. "
        "좁은 폭에 드롭다운을 얹으면 지도가 다 덮인다</td></tr>"
        "</table>"
        "<h2><span class=n>남은</span>정할 것</h2>"
        "<ul class=k>"
        "<li><b>도시가 여러 출발지에 있으면</b> 어느 걸 여나 &mdash; 지금 출발지 우선, "
        "없으면 다른 출발지를 제안(S5)으로 잡았다. 확정 필요.</li>"
        "<li><b>검색 결과에도 도장을 보이나</b> &mdash; 지금은 가격만 뒀다. "
        "도장까지 넣으면 목록이 무거워진다.</li>"
        "<li><b>최근 검색 기억</b> &mdash; <code>localStorage</code>가 필요하고, "
        "지금 URL 상태만 쓰기로 한 것과 결이 다르다. 뒤로 미룬다.</li>"
        "</ul>"
        "<p class=note>&#9888; <b>이 세션엔 브라우저가 없어 실제 렌더를 못 본다.</b> "
        "겹치거나 어색한 곳이 있으면 알려주면 고친다.</p>"
        "<p class=foot>생성 <b>design/build_search.py</b> &middot; 데이터 <b>docs/data/deals.json</b> &middot; "
        "위치·크기 비교 <b>dockbar.html</b> &middot; 확정 홈 <b>home.html</b> &middot; "
        "스펙 <b>../SPEC.md</b></p>"
        "</div></body></html>")

io.open(os.path.join(BASE, "search.html"), "w", encoding="utf-8").write(html)
print("search.html  %.1fKB" % (len(html) / 1024.0))
print("  states: %d" % len(STATES))
print("  '%s' hits: tags=%s cities=%s" % (q, hit_tags, [d["ko"] for d in hit_city]))
print("  miss case: %s (alt=%s)" % (miss, alt[0]["o"] if alt else "none"))
