# -*- coding: utf-8 -*-
"""날짜·예산 필터 설계.

검색 바(G2) 오른쪽 알약 둘이 여는 팝오버다. 실제 deals.json 분포로 그린다.
건수는 전부 실측이다 — 필터가 무엇을 걸러낼지 미리 보여주는 게 이 설계의 핵심이다.
소유: 기획 세션. 산출물 design/filters.html
"""
import json, io, os, sys, collections

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
from _app import CSS
from _fmt import money

D = json.load(io.open(os.path.join(BASE, "..", "docs", "data", "deals.json"), encoding="utf-8"))
deals = D["deals"]
N = len(deals)


def nights_n(d):
    """`nights`는 '3박4일' 같은 표시용 문자열이다. 앞의 숫자만 뽑는다."""
    s = d.get("nights", "")
    num = ""
    for ch in s:
        if ch.isdigit():
            num += ch
        else:
            break
    return int(num) if num else None


# ── 실측 ───────────────────────────────────────────────────────
WHEN_ORDER = ["이번 주말", "이번 주", "이번 달", "다음 달"]
wc = collections.Counter(d.get("when", "") for d in deals)
later = sum(v for k, v in wc.items() if k not in WHEN_ORDER)

NIGHT_BUCKETS = [("1~3박", 1, 3), ("4~6박", 4, 6), ("7~13박", 7, 13), ("2주 이상", 14, 999)]
nb = []
for lab, lo, hi in NIGHT_BUCKETS:
    nb.append((lab, sum(1 for d in deals if (nights_n(d) or 0) and lo <= nights_n(d) <= hi)))
no_nights = sum(1 for d in deals if nights_n(d) is None)

PRICE_CUTS = [300000, 500000, 1000000]
pc = [(c, sum(1 for d in deals if d["price"] <= c)) for c in PRICE_CUTS]
over_slider = sum(1 for d in deals if d["price"] > 1000000)
under_slider = sum(1 for d in deals if d["price"] < 100000)

ps = sorted(d["price"] for d in deals)
med = ps[len(ps) // 2]

# 히스토그램(로그 눈금) — 가격이 33천~138만이라 선형으로는 왼쪽에 다 뭉친다
import math
lo_p, hi_p = ps[0], ps[-1]
BINS = 26
hist = [0] * BINS
for p in ps:
    t = (math.log(p) - math.log(lo_p)) / (math.log(hi_p) - math.log(lo_p))
    hist[min(BINS - 1, int(t * BINS))] += 1
hmax = max(hist)

EXTRA = """
.wrapF{max-width:1060px;margin:0 auto;padding:44px 26px 90px}
.pair{display:flex;gap:22px;flex-wrap:wrap;align-items:flex-start;margin-bottom:34px}
.opt{width:498px}
.ohd{display:flex;align-items:baseline;gap:8px;margin-bottom:4px}
.oid{font-size:.64rem;font-weight:900;background:var(--ink);color:#fff;border-radius:4px;padding:2px 7px}
.onm{font-weight:800;font-size:.92rem}
.rec{font-size:.55rem;font-weight:900;background:var(--accent);color:#fff;border-radius:4px;padding:2px 6px;vertical-align:2px}
.no{font-size:.55rem;font-weight:900;background:var(--sub);color:#fff;border-radius:4px;padding:2px 6px;vertical-align:2px}
.odesc{color:var(--sub);font-size:.78rem;line-height:1.62;min-height:56px;margin:5px 0 10px}
.hold{background:var(--sea);border:1px solid #cfdad7;border-radius:14px;padding:16px}
.barline{display:flex;align-items:center;gap:8px;margin-bottom:10px}
.sbar{flex:1;background:#fff;border:1px solid var(--line);border-radius:11px;height:46px;
 display:flex;align-items:center;gap:8px;padding:0 12px}
.mag{color:var(--sub);font-size:.86rem}
.ph{font-size:.78rem;color:var(--sub);font-weight:600}
.spill2{background:var(--soft);border:1px solid var(--line);border-radius:99px;padding:5px 12px;
 font-size:.72rem;font-weight:800;color:var(--sub);white-space:nowrap}
.spill2.on{background:var(--accent);color:#fff;border-color:var(--accent)}
.pv{background:#fff;border:1px solid var(--line);border-radius:12px;padding:12px 13px;
 box-shadow:0 10px 26px rgba(16,44,38,.15)}
.pvg{font-size:.62rem;font-weight:800;color:var(--sub);margin:11px 2px 7px;display:flex;gap:7px;align-items:center}
.pvg:first-child{margin-top:1px}
.pvg .line{flex:1;height:1px;background:var(--line)}
.chips2{display:flex;gap:6px;flex-wrap:wrap}
.ch{background:var(--soft);border:1px solid var(--line);border-radius:99px;padding:5px 12px;
 font-size:.76rem;font-weight:800;color:var(--ink);display:inline-flex;align-items:baseline;gap:6px}
.ch .n{font-size:.66rem;color:var(--sub);font-weight:700;font-variant-numeric:tabular-nums}
.ch.on{background:var(--accent);color:#fff;border-color:var(--accent)}
.ch.on .n{color:#fff9}
.ch.dim{opacity:.45}
.ch.dim .n{color:var(--sub)}
/* 슬라이더 */
.sl{position:relative;height:6px;background:var(--line);border-radius:99px;margin:16px 4px 8px}
.sl i{position:absolute;left:0;top:0;bottom:0;border-radius:99px;background:var(--accent)}
.sl .kn{position:absolute;top:-6px;width:18px;height:18px;border-radius:99px;background:#fff;
 border:2px solid var(--accent);box-shadow:0 2px 6px #0002;margin-left:-9px}
.slv{display:flex;justify-content:space-between;font-size:.68rem;font-weight:800;color:var(--sub)}
.hist{display:flex;align-items:flex-end;gap:2px;height:44px;margin:4px 4px 0}
.hist i{flex:1;background:#C9DAD6;border-radius:2px 2px 0 0;min-height:2px}
.hist i.on{background:var(--accent)}
.warn{background:#FFF4F1;border:1px solid #F6C9BB;border-radius:9px;padding:9px 11px;
 font-size:.74rem;line-height:1.6;margin-top:10px}
.warn b{color:var(--accent)}
.ok2{background:#F1F8F4;border:1px solid #C6E3D2;border-radius:9px;padding:9px 11px;
 font-size:.74rem;line-height:1.6;margin-top:10px}
.ok2 b{color:#1E7A50}
"""

BAR = ('<div class="barline"><div class="sbar"><span class="mag">&#9906;</span>'
       '<span class="ph">어디로 갈까요?</span></div>%s</div>')


def chips(items, on=None, dim=()):
    out = ""
    for lab, cnt in items:
        cls = " on" if lab == on else (" dim" if lab in dim else "")
        out += ('<span class="ch%s">%s<span class="n">%s</span></span>'
                % (cls, lab, cnt if cnt != "" else ""))
    return '<div class="chips2">%s</div>' % out


# ══ 날짜 ══════════════════════════════════════════════════════
when_items = [(k, wc.get(k, 0)) for k in WHEN_ORDER] + [("그 이후", later)]

# ⚠️ 아래 문자열에는 CSS의 리터럴 `%`(width:100%)가 섞인다.
#    % 서식 연산자를 문자열 전체에 걸면 그걸 서식 문자로 읽어 터진다.
#    동적인 값은 **먼저** 변수로 만들어 두고 연결만 한다.
_unreach = wc.get("이번 달", 0) + later
_unreach_pct = "%.0f" % (100.0 * _unreach / N)

D1 = (BAR % '<span class="spill2 on">아무때 &#9662;</span>'
      + '<div class="pv"><div class="pvg">언제<span class="line"></span></div>'
      + chips([("아무때", N)] + [(k, wc.get(k, 0)) for k in ["이번 주", "이번 주말", "다음 달"]]
              + [("날짜 지정", "")], on="아무때")
      + '<div class="warn">현행 칩엔 <b>이번 달</b>도 <b>그 이후</b>도 없다. '
        '<b>이번 달 ' + str(wc.get("이번 달", 0)) + '건 + 그 이후 ' + str(later) + '건 = '
        + str(_unreach) + '건(' + _unreach_pct + '%)</b> &mdash; '
        '<b>절반이 넘는 딜을 &lsquo;그것만&rsquo; 골라낼 수가 없다.</b><br>'
        '<span style="color:var(--sub)">보이긴 한다(<code>아무때</code>로). '
        '못 하는 건 <b>좁히는 것</b>이다.</span></div></div>')

D2 = (BAR % '<span class="spill2 on">이번 달 &middot; 3~4박 &#9662;</span>'
      + '<div class="pv"><div class="pvg">언제<span class="line"></span></div>'
      + chips([("아무때", N)] + when_items + [("날짜 지정", "")], on="이번 달")
      + '<div class="pvg">며칠<span class="line"></span></div>'
      + chips([("상관없어", N)] + nb, on="1~3박")
      + '<div class="ok2"><b>&lsquo;며칠&rsquo;은 지금 필터에 없다.</b> '
        '<code>nights</code> 필드가 이미 있는데 안 쓰고 있었다 &mdash; '
        '<b>주말 2박3일</b>과 <b>일주일 휴가</b>는 전혀 다른 여행인데 지금은 못 가른다.</div></div>')

_cal = "".join('<div>' + w + '</div>' for w in "월화수목금토일")
for _i in range(1, 29):
    _st = ("background:var(--accent);color:#fff;font-weight:900"
           if 8 <= _i <= 16 else "color:var(--ink)")
    _cal += '<div style="padding:5px 0;border-radius:6px;' + _st + '">' + str(_i) + '</div>'

D3 = (BAR % '<span class="spill2 on">9/8 ~ 9/16 &#9662;</span>'
      + '<div class="pv"><div class="pvg">직접 고르기<span class="line"></span></div>'
        '<div style="display:grid;grid-template-columns:repeat(7,1fr);gap:3px;font-size:.66rem;'
        'text-align:center;font-weight:700;color:var(--sub);padding:2px">' + _cal
      + '</div><div class="warn">달력은 <b>목적지가 정해진 사람</b>의 도구다. '
        '우리 사용자는 <b>날짜가 먼저 정해져 있고 목적지를 찾는다</b> &mdash; '
        '&lsquo;휴가가 10월 셋째 주&rsquo; 같은. 그건 <b>칩으로 충분</b>하고, '
        '달력은 <b>&lsquo;날짜 지정&rsquo;을 눌렀을 때만</b> 있으면 된다.</div></div>')

# ══ 예산 ══════════════════════════════════════════════════════
_miss = over_slider + under_slider
_miss_pct = "%.0f" % (100.0 * _miss / N)

B1 = (BAR % '<span class="spill2 on">100만 이하 &#9662;</span>'
      + '<div class="pv"><div class="pvg">예산<span class="line"></span></div>'
        '<div class="sl"><i style="width:100%"></i><span class="kn" style="left:100%"></span></div>'
        '<div class="slv"><span>10만</span><span>100만</span></div>'
        '<div class="warn">범위가 <b>10만~100만</b>인데 실제 딜은 <b>'
      + money(lo_p) + ' ~ ' + money(hi_p) + '원</b>이다. <b>'
      + str(_miss) + '건(' + _miss_pct + '%)이 슬라이더 밖</b>에 있다 &mdash; '
        '오른쪽 끝까지 밀어도 안 나온다. 게다가 값이 <b>40배 범위</b>라 '
        '선형 슬라이더는 눈금 대부분을 <b>딜이 거의 없는 고가 구간</b>에 쓴다.</div></div>')

on_bin = int(BINS * (math.log(500000) - math.log(lo_p)) / (math.log(hi_p) - math.log(lo_p)))

B2 = (BAR % '<span class="spill2 on">50만 이하 &#9662;</span>'
      + '<div class="pv"><div class="pvg">예산<span class="line"></span></div>'
      + chips([(str(c // 10000) + "만 이하", n) for c, n in pc] + [("상관없어", N)],
              on="50만 이하")
      + '<div class="ok2"><b>건수를 같이 보인다</b> &mdash; 누르기 전에 '
        '<b>몇 곳이 남는지</b> 안다. 지금 슬라이더는 밀어봐야 안다.<br>'
        '경계는 실제 분포에서 뽑았다 &mdash; 중앙값 <b>' + money(med) + '원</b>, <b>'
      + '30만 ' + str(100 * pc[0][1] // N) + '% · '
      + '50만 ' + str(100 * pc[1][1] // N) + '% · '
      + '100만 ' + str(100 * pc[2][1] // N) + '%</b>.</div></div>')

_bars = ""
for _i, _h in enumerate(hist):
    _cls = "on" if _i <= on_bin else ""
    _bars += ('<i class="' + _cls + '" style="height:'
              + str(max(4, int(100.0 * _h / hmax))) + '%"></i>')
_pos = str(int(100.0 * on_bin / BINS))

B3 = (BAR % '<span class="spill2 on">50만 이하 &#9662;</span>'
      + '<div class="pv"><div class="pvg">예산<span class="line"></span></div>'
        '<div class="hist">' + _bars
      + '</div><div class="sl" style="margin-top:2px"><i style="width:' + _pos + '%"></i>'
        '<span class="kn" style="left:' + _pos + '%"></span></div>'
        '<div class="slv"><span>' + money(lo_p) + '</span><span>50만</span><span>'
      + money(hi_p) + '</span></div>'
        '<div class="ok2">막대가 <b>딜이 실제로 어디 몰려 있는지</b> 보여준다. '
        '눈금은 <b>로그</b>라 저가 구간이 뭉치지 않는다.<br>'
        '다만 <b>손으로 정밀하게 맞춰야</b> 하고, 모바일에서 얇은 손잡이를 끄는 건 어렵다.</div></div>')

DATE_OPTS = [
    ("D1", "현행 + 이번 달만 추가", "현행", "no",
     "칩 다섯을 그대로 두고 <code>이번 달</code>만 넣는다. 가장 작은 변화지만 "
     "<b>&lsquo;그 이후&rsquo;가 여전히 없다.</b>", D1),
    ("D2", "언제 &times; 며칠 &mdash; 두 축", "추천", "rec",
     "<code>when</code> 어휘를 그대로 칩으로 쓰고(빈 구간이 없어진다), "
     "<b>&lsquo;며칠&rsquo; 축을 새로 넣는다.</b> 데이터에 이미 있는데 안 쓰던 것이다.", D2),
    ("D3", "달력", "", "",
     "직접 날짜를 고른다. 정확하지만 <b>결정을 사용자에게 떠넘긴다.</b>", D3),
]

BUDGET_OPTS = [
    ("B1", "슬라이더", "현행", "no",
     "10만~100만 범위를 손으로 민다. <b>범위 밖 딜이 %d건</b>이고, "
     "누르기 전엔 몇 곳이 남는지 모른다." % (over_slider + under_slider), B1),
    ("B2", "프리셋 + 건수", "추천", "rec",
     "<b>30만 / 50만 / 100만 / 상관없어</b> 넷. 실제 분포에서 경계를 뽑았고 "
     "<b>건수를 같이 보인다.</b>", B2),
    ("B3", "히스토그램 슬라이더", "", "",
     "딜이 몰린 곳을 막대로 보이고 로그 눈금을 쓴다. 정보량은 가장 많지만 "
     "<b>정밀 조작</b>이 필요하다.", B3),
]


def block(title, opts):
    out = '<h2><span class="n">%s</span></h2><div class="pair">' % title
    for oid, nm, badge, cls, desc, mk in opts:
        b = ('<span class="rec">추천</span>' if cls == "rec"
             else '<span class="no">현행</span>' if cls == "no" else "")
        out += ('<div class="opt"><div class="ohd"><span class="oid">%s</span>'
                '<span class="onm">%s</span>%s</div><div class="odesc">%s</div>'
                '<div class="hold">%s</div></div>' % (oid, nm, b, desc, mk))
    return out + '</div>'


html = ("<!doctype html><html lang=ko><head><meta charset=utf-8>"
        "<meta name=viewport content='width=device-width,initial-scale=1'>"
        "<title>갈래말래 — 날짜·예산 필터</title><style>" + CSS + EXTRA +
        "</style></head><body><div class=wrapF>"
        "<h1>날짜 &middot; 예산 &mdash; <em>검색 바 오른쪽 알약 둘</em></h1>"
        "<p class=lede>검색창에 <b>안 넣기로 한 둘</b>이다 &mdash; 값이 <b>범위</b>라 타이핑으로 고르기 나쁘다. "
        "실제 " + str(N) + "건 분포로 그렸고 <b>건수는 전부 실측</b>이다.</p>"
        "<div class=callout><b>먼저 &mdash; 지금 둘 다 구멍이 있다.</b><br>"
        "<b>날짜</b>: 칩에 <code>이번 달</code>도 <code>그 이후</code>도 없어 "
        "<b>" + str(_unreach) + "건(" + _unreach_pct + "%)</b>을 <b>골라낼 수가 없다</b>"
        " &mdash; 보이긴 하지만 좁히지를 못한다.<br>"
        "<b>예산</b>: 슬라이더 범위가 10만~100만인데 실제는 " + money(lo_p) + "~" + money(hi_p) + "원이라 "
        "<b>" + str(over_slider + under_slider) + "건이 밖</b>에 있다.<br>"
        "<b>그리고 <code>nights</code>를 아무도 안 쓰고 있었다</b> &mdash; "
        "주말 2박3일과 일주일 휴가를 못 가른다.</div>"
        + block("날짜", DATE_OPTS)
        + block("예산", BUDGET_OPTS) +
        "<h2><span class=n>왜</span>D2 + B2</h2>"
        "<ul class=k>"
        "<li><b>칩을 <code>when</code> 어휘와 맞춘다.</b> 화면에 뜨는 라벨과 고르는 칩이 "
        "같은 말이면 배울 게 없다. 빈 구간도 사라진다.</li>"
        "<li><b>&lsquo;며칠&rsquo;이 진짜 빠진 축이다.</b> 데이터에 <code>nights</code>가 있는데 "
        "안 쓰고 있었다. 실측 <b>1~3박 %d건 · 4~6박 %d건 · 7~13박 %d건 · 2주 이상 %d건</b> &mdash; "
        "고르게 퍼져 있어 필터로서 값이 있다.</li>"
        "<li><b>예산은 프리셋이 맞다.</b> 값이 40배 범위라 선형 슬라이더는 눈금을 낭비하고, "
        "사람은 애초에 <b>&lsquo;30만 안쪽&rsquo;</b>처럼 어림으로 생각한다.</li>"
        "<li><b>건수를 보이는 게 핵심이다.</b> 지금은 필터를 걸고 나서야 결과를 안다. "
        "<b>누르기 전에 아는 것</b>과 후에 아는 것은 다르다 &mdash; "
        "0곳이 될 칩을 누르게 두지 않는다.</li>"
        "<li><b>달력은 &lsquo;날짜 지정&rsquo; 안에만.</b> 달력은 목적지가 정해진 사람의 도구다. "
        "우리 사용자는 반대다 &mdash; 날짜가 먼저 있고 목적지를 찾는다.</li>"
        "</ul>"
        "<p class=note>&#9888; <b>칩 개수가 늘어난다</b>(언제 6 + 며칠 5). 팝오버 안이라 "
        "지도를 안 가리지만, 모바일에서 두 줄이 될지는 폭을 봐야 안다. "
        "이 세션엔 브라우저가 없어 확인을 못 한다.</p>"
        "<p class=foot>생성 <b>design/build_filters.py</b> &middot; 데이터 <b>docs/data/deals.json</b> "
        "&middot; 검색 바 <b>search.html</b> &middot; 확정 홈 <b>home.html</b></p>"
        "</div></body></html>"
        % (nb[0][1], nb[1][1], nb[2][1], nb[3][1]))

io.open(os.path.join(BASE, "filters.html"), "w", encoding="utf-8").write(html)
print("filters.html  %.1fKB" % (len(html) / 1024.0))
print("  when: " + " / ".join("%s %d" % (k, wc.get(k, 0)) for k in WHEN_ORDER) + " / 그이후 %d" % later)
print("  nights: " + " / ".join("%s %d" % (a, b) for a, b in nb) + " / 없음 %d" % no_nights)
print("  price: " + " / ".join("%d만 %d건" % (c // 10000, n) for c, n in pc))
print("  slider miss: %d (over %d, under %d)" % (over_slider + under_slider, over_slider, under_slider))
