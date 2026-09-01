# -*- coding: utf-8 -*-
"""예산 필터 — 데스크톱과 모바일을 어떻게 가를까.

사용자 판단(2026-09-01): "웹에서는 B3(히스토그램)가 좋고, B2(프리셋)는 모바일 어때?"
그 직감을 검증하고, 갈라놓는 것보다 나은 안이 있는지 본다.
실제 deals.json 분포로 그린다.
소유: 기획 세션. 산출물 design/budget.html
"""
import json, io, os, sys, math

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
from _app import CSS
from _fmt import money

D = json.load(io.open(os.path.join(BASE, "..", "docs", "data", "deals.json"), encoding="utf-8"))
deals = D["deals"]
N = len(deals)
ps = sorted(d["price"] for d in deals)
lo_p, hi_p = ps[0], ps[-1]
med = ps[len(ps) // 2]

CUTS = [300000, 500000, 1000000]
pc = [(c, sum(1 for d in deals if d["price"] <= c)) for c in CUTS]

BINS = 24
hist = [0] * BINS
for p in ps:
    t = (math.log(p) - math.log(lo_p)) / (math.log(hi_p) - math.log(lo_p))
    hist[min(BINS - 1, int(t * BINS))] += 1
hmax = max(hist)


def bin_of(v):
    v = max(lo_p, min(hi_p, v))
    return int(BINS * (math.log(v) - math.log(lo_p)) / (math.log(hi_p) - math.log(lo_p)))


def hist_html(upto_bin, klass=""):
    out = '<div class="hist ' + klass + '">'
    for i, h in enumerate(hist):
        on = "on" if i <= upto_bin else ""
        out += ('<i class="' + on + '" style="height:'
                + str(max(5, int(100.0 * h / hmax))) + '%"></i>')
    return out + '</div>'


# 터치 타깃 (iOS HIG 44pt · Material 48dp)
TOUCH_MIN = 44
KNOB_DESK = 18
KNOB_MOB = 44
CHIP_H = 34

EXTRA = """
.wrapB{max-width:1120px;margin:0 auto;padding:44px 26px 90px}
.row{display:flex;gap:24px;flex-wrap:wrap;align-items:flex-start;margin-bottom:30px}
.card2{background:#fff;border:1px solid var(--line);border-radius:14px;padding:16px 17px}
.hd{display:flex;align-items:baseline;gap:8px;margin-bottom:4px}
.hid{font-size:.63rem;font-weight:900;background:var(--ink);color:#fff;border-radius:4px;padding:2px 7px}
.hnm{font-weight:800;font-size:.9rem}
.rec{font-size:.55rem;font-weight:900;background:var(--accent);color:#fff;border-radius:4px;padding:2px 6px;vertical-align:2px}
.hdesc{color:var(--sub);font-size:.77rem;line-height:1.6;margin:4px 0 12px;min-height:52px}
/* 데스크톱 팝오버 */
.pop3{width:262px;background:#fff;border:1px solid var(--line);border-radius:12px;
 padding:12px 13px;box-shadow:0 10px 26px rgba(16,44,38,.15)}
/* 모바일 시트 */
.phone{width:390px;background:var(--sea);border:1px solid #cfdad7;border-radius:20px;
 overflow:hidden;position:relative;height:400px}
.phone .map{position:absolute;inset:0;background:
 radial-gradient(120px 90px at 30% 26%,var(--land),transparent 70%),
 radial-gradient(90px 70px at 72% 50%,var(--land),transparent 70%),var(--sea)}
.sheet2{position:absolute;left:0;right:0;bottom:0;background:#fff;
 border-radius:18px 18px 0 0;padding:10px 16px 20px;box-shadow:0 -10px 30px rgba(16,44,38,.18)}
.grab{width:38px;height:4px;border-radius:99px;background:#c3cfcc;margin:0 auto 12px}
.stitle{font-size:.9rem;font-weight:800;margin-bottom:10px}
.pvg{font-size:.62rem;font-weight:800;color:var(--sub);margin:12px 2px 8px;display:flex;gap:7px;align-items:center}
.pvg:first-child{margin-top:2px}
.pvg .line{flex:1;height:1px;background:var(--line)}
.chips2{display:flex;gap:6px;flex-wrap:wrap}
.ch{background:var(--soft);border:1px solid var(--line);border-radius:99px;
 font-size:.76rem;font-weight:800;color:var(--ink);display:inline-flex;align-items:center;gap:6px;
 padding:0 13px;height:34px}
.ch.big{height:44px;padding:0 16px;font-size:.82rem;border-radius:12px}
.ch .n{font-size:.66rem;color:var(--sub);font-weight:700;font-variant-numeric:tabular-nums}
.ch.on{background:var(--accent);color:#fff;border-color:var(--accent)}
.ch.on .n{color:#fff9}
/* 히스토그램 + 슬라이더 */
.hist{display:flex;align-items:flex-end;gap:2px;height:46px;margin:2px 0 0}
.hist.tall{height:62px}
.hist i{flex:1;background:#C9DAD6;border-radius:2px 2px 0 0;min-height:3px}
.hist i.on{background:var(--accent)}
.track{position:relative;height:6px;background:var(--line);border-radius:99px;margin:9px 0 0}
.track i{position:absolute;left:0;top:0;bottom:0;border-radius:99px;background:var(--accent)}
.knob{position:absolute;border-radius:99px;background:#fff;border:2px solid var(--accent);
 box-shadow:0 2px 8px rgba(20,50,45,.2)}
.knob.d{width:18px;height:18px;top:-6px;margin-left:-9px}
.knob.m{width:44px;height:44px;top:-19px;margin-left:-22px;
 display:flex;align-items:center;justify-content:center}
.knob.m:after{content:"";width:14px;height:14px;border-radius:99px;background:var(--accent)}
.vals{display:flex;justify-content:space-between;font-size:.68rem;font-weight:800;
 color:var(--sub);margin-top:11px;font-variant-numeric:tabular-nums}
.vals b{color:var(--accent);font-size:.86rem}
.tt{display:flex;gap:8px;margin-top:12px}
.tt div{flex:1;border:1px solid var(--line);border-radius:9px;padding:7px 9px;font-size:.7rem;
 line-height:1.45;text-align:center}
.tt b{display:block;font-size:1.02rem;letter-spacing:-.02em}
.tt .bad b{color:var(--accent)}
.tt .good b{color:#1E7A50}
.warn{background:#FFF4F1;border:1px solid #F6C9BB;border-radius:9px;padding:9px 11px;
 font-size:.74rem;line-height:1.6;margin-top:11px}
.warn b{color:var(--accent)}
.ok2{background:#F1F8F4;border:1px solid #C6E3D2;border-radius:9px;padding:9px 11px;
 font-size:.74rem;line-height:1.6;margin-top:11px}
.ok2 b{color:#1E7A50}
"""

b50 = bin_of(500000)
pos = int(100.0 * b50 / (BINS - 1))
n50 = pc[1][1]

CHIPS = "".join('<span class="ch' + (" on" if c == 500000 else "") + '">'
                + str(c // 10000) + '만 이하<span class="n">' + str(n) + '</span></span>'
                for c, n in pc) + \
        '<span class="ch">상관없어<span class="n">' + str(N) + '</span></span>'
CHIPS_BIG = CHIPS.replace('class="ch', 'class="ch big').replace('ch big on', 'ch big on')

VALS = ('<div class="vals"><span>' + money(lo_p) + '원</span>'
        '<b>50만원 이하 · ' + str(n50) + '곳</b>'
        '<span>' + money(hi_p) + '원</span></div>')

# ── 데스크톱 ───────────────────────────────────────────────────
W1 = ('<div class="pop3"><div class="pvg">예산<span class="line"></span></div>'
      + hist_html(b50)
      + '<div class="track"><i style="width:' + str(pos) + '%"></i>'
        '<span class="knob d" style="left:' + str(pos) + '%"></span></div>'
      + VALS + '</div>')

W2 = ('<div class="pop3"><div class="pvg">예산<span class="line"></span></div>'
      + hist_html(b50)
      + '<div class="track"><i style="width:' + str(pos) + '%"></i>'
        '<span class="knob d" style="left:' + str(pos) + '%"></span></div>'
      + VALS
      + '<div class="pvg">빠르게<span class="line"></span></div>'
        '<div class="chips2">' + CHIPS + '</div></div>')

# ── 모바일 ─────────────────────────────────────────────────────
def phone(inner):
    return ('<div class="phone"><div class="map"></div>'
            '<div class="sheet2"><div class="grab"></div>'
            '<div class="stitle">예산</div>' + inner + '</div></div>')


M1 = phone('<div class="chips2">' + CHIPS_BIG + '</div>')

M2 = phone(hist_html(b50, "tall")
           + '<div class="track" style="margin-top:22px"><i style="width:' + str(pos) + '%"></i>'
             '<span class="knob m" style="left:' + str(pos) + '%"></span></div>'
           + VALS)

M3 = phone('<div class="chips2">' + CHIPS_BIG + '</div>'
           + '<div class="pvg">정확히<span class="line"></span></div>'
           + hist_html(b50)
           + '<div class="track" style="margin-top:22px"><i style="width:' + str(pos) + '%"></i>'
             '<span class="knob m" style="left:' + str(pos) + '%"></span></div>'
           + VALS)

TT_BAD = ('<div class="tt"><div class="bad"><b>' + str(KNOB_DESK) + 'px</b>손잡이</div>'
          '<div class="bad"><b>' + str(TOUCH_MIN) + 'px</b>필요</div>'
          '<div class="bad"><b>' + str(round(TOUCH_MIN / float(KNOB_DESK), 1)) + '배</b>모자람</div></div>')
TT_OK = ('<div class="tt"><div class="good"><b>' + str(KNOB_MOB) + 'px</b>손잡이</div>'
         '<div class="good"><b>' + str(TOUCH_MIN) + 'px</b>필요</div>'
         '<div class="good"><b>✓</b>충족</div></div>')
TT_CHIP = ('<div class="tt"><div class="good"><b>' + str(KNOB_MOB) + 'px</b>칩 높이</div>'
           '<div class="good"><b>' + str(TOUCH_MIN) + 'px</b>필요</div>'
           '<div class="good"><b>✓</b>충족</div></div>')

DESK = [
    ("W1", "히스토그램 + 슬라이더", "", W1,
     "사용자가 고른 <b>B3</b>. 막대가 <b>딜이 실제로 어디 몰려 있는지</b> 보여주고 "
     "눈금은 로그라 저가 구간이 안 뭉친다. 마우스는 정밀 조작이 쉬우니 데스크톱에선 문제없다."),
    ("W2", "히스토그램 + <b>바로가기 칩</b>", "추천", W2,
     "같은 슬라이더에 <b>칩을 아래 얹었다.</b> 칩은 슬라이더를 그 값으로 옮기는 <b>바로가기</b>다. "
     "&mdash; 대충 정하는 사람은 <b>누르고</b>, 정확히 맞추는 사람은 <b>끈다</b>."),
]

MOB = [
    ("M1", "프리셋만", "", M1,
     "사용자가 제안한 <b>B2</b>. 칩 높이를 <b>44px</b>로 키우면 터치에 딱 맞는다. "
     "가장 단순하지만 <b>히스토그램이 주는 정보를 잃는다</b> &mdash; "
     "&lsquo;어디에 딜이 몰려 있나&rsquo;를 모바일 사용자만 못 본다." + TT_CHIP),
    ("M2", "슬라이더만", "", M2,
     "손잡이를 <b>44px</b>로 키우면 터치는 된다. 다만 <b>시트를 끌어 내리는 제스처</b>와 "
     "손잡이 드래그가 <b>같은 방향에서 부딪힌다</b> &mdash; 시트가 닫혀버리기 쉽다." + TT_OK),
    ("M3", "칩 + 슬라이더 <b>둘 다</b>", "추천", M3,
     "W2와 <b>같은 구조</b>다. 칩이 위, 슬라이더가 아래. "
     "모바일에선 대부분 칩으로 끝나고 슬라이더는 <b>필요한 사람만</b> 쓴다.<br>"
     "<b>데스크톱과 같은 물건이라 배울 게 없다.</b>" + TT_CHIP),
]


def block(title, items, wide=False):
    out = '<h2><span class="n">' + title + '</span></h2><div class="row">'
    for hid, nm, badge, mk, desc in items:
        b = '<span class="rec">추천</span>' if badge else ""
        out += ('<div class="card2" style="width:' + ("330" if not wide else "424") + 'px">'
                '<div class="hd"><span class="hid">' + hid + '</span>'
                '<span class="hnm">' + nm + '</span>' + b + '</div>'
                '<div class="hdesc">' + desc + '</div>' + mk + '</div>')
    return out + '</div>'


html = ("<!doctype html><html lang=ko><head><meta charset=utf-8>"
        "<meta name=viewport content='width=device-width,initial-scale=1'>"
        "<title>갈래말래 — 예산 필터</title><style>" + CSS + EXTRA +
        "</style></head><body><div class=wrapB>"
        "<h1>예산 &mdash; <em>데스크톱과 모바일</em></h1>"
        "<p class=lede>&ldquo;웹에서는 B3가 좋고 B2는 모바일 어때?&rdquo;라는 판단을 검증했다. "
        "<b>방향은 맞다</b> &mdash; 슬라이더 손잡이는 터치에 너무 작다. "
        "다만 <b>둘을 갈라놓는 것보다 합치는 쪽</b>이 나아 보여 그 안을 같이 그렸다. "
        "실제 " + str(N) + "건 분포다.</p>"
        "<div class=callout><b>슬라이더 손잡이는 터치 최소 크기의 절반도 안 된다.</b><br>"
        "데스크톱 손잡이가 <b>" + str(KNOB_DESK) + "px</b>인데 터치 최소는 <b>" + str(TOUCH_MIN) + "px</b>다"
        "(iOS 44pt · Material 48dp). <b>2.4배 모자라</b> 손가락으로는 못 집는다. "
        "그래서 모바일에 그대로 못 쓴다는 판단이 맞다.<br>"
        "<b>다만 히스토그램은 손잡이와 별개다.</b> 막대는 <b>읽는 것</b>이지 <b>집는 것</b>이 아니라 "
        "모바일에서도 그대로 쓸 수 있다 &mdash; 그걸 버릴 이유가 없다.</div>"
        + block("데스크톱", DESK)
        + block("모바일 390px", MOB) +
        "<h2><span class=n>왜</span>W2 + M3 &mdash; 갈라놓지 않는다</h2>"
        "<ul class=k>"
        "<li><b>칩과 슬라이더는 경쟁하지 않는다.</b> 칩은 <b>슬라이더를 그 값으로 옮기는 바로가기</b>이고, "
        "슬라이더는 그 사이 값을 고르는 도구다. 하나를 고르는 문제가 아니었다.</li>"
        "<li><b>히스토그램을 모바일에서 뺄 이유가 없다.</b> 막대는 읽는 것이라 터치 크기와 무관하다. "
        "빼면 <b>&lsquo;딜이 어디 몰려 있나&rsquo;를 모바일 사용자만 못 본다.</b></li>"
        "<li><b>같은 물건이면 배울 게 없다.</b> 기기마다 다른 UI를 주면 "
        "&lsquo;내 폰에는 왜 없지&rsquo;가 생긴다. 우리 사용자는 <b>폰으로 보고 데스크톱에서 예약</b>할 가능성이 높다.</li>"
        "<li><b>모바일 손잡이는 44px로 키운다.</b> 다만 <b>시트 끌기와 방향이 겹치므로</b> "
        "슬라이더를 잡는 동안 시트 드래그를 막아야 한다 &mdash; 프론트 구현 시 주의.</li>"
        "<li><b>실측 경계</b> &mdash; 중앙값 <b>" + money(med) + "원</b>, "
        "<b>30만 " + str(pc[0][1]) + "곳 · 50만 " + str(pc[1][1]) + "곳 · 100만 " + str(pc[2][1]) + "곳</b>. "
        "칩 경계는 여기서 뽑았다.</li>"
        "</ul>"
        "<p class=note>&#9888; <b>칩만 쓰는 M1도 나쁘지 않다.</b> 모바일에서 정밀 예산을 맞추는 사람이 "
        "정말 있는지는 <b>안 써보면 모른다.</b> 구현이 부담되면 <b>M1으로 시작하고 슬라이더는 나중에</b> "
        "붙여도 된다 &mdash; 칩이 슬라이더의 바로가기라 나중에 얹어도 구조가 안 깨진다.</p>"
        "<p class=note>&#9888; 이 세션엔 브라우저가 없어 실제 렌더를 못 본다. "
        "모바일 시트 높이가 지도를 얼마나 덮는지는 봐야 안다.</p>"
        "<p class=foot>생성 <b>design/build_budget.py</b> &middot; 데이터 <b>docs/data/deals.json</b> "
        "&middot; 날짜·예산 비교 <b>filters.html</b> &middot; 검색 바 <b>search.html</b></p>"
        "</div></body></html>")

io.open(os.path.join(BASE, "budget.html"), "w", encoding="utf-8").write(html)
print("budget.html  %.1fKB" % (len(html) / 1024.0))
print("  knob desktop %dpx vs touch min %dpx  -> %.1fx short"
      % (KNOB_DESK, TOUCH_MIN, TOUCH_MIN / float(KNOB_DESK)))
print("  cuts: " + " / ".join("%d man %d" % (c // 10000, n) for c, n in pc))
print("  median %s  range %s ~ %s" % (money(med), money(lo_p), money(hi_p)))
