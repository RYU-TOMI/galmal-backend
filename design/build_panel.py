# -*- coding: utf-8 -*-
"""패널 폭 — 좁히면 지구가 커지고, 넓히면 카드가 여유로워진다.

둘 다 실측으로 잰다.
  지도 쪽 — viewBox 1000x680 고정 + slice 크롭에서 나오는 far 배율
  카드 쪽 — 실제 도시명·가격 문자열 폭으로 "몇 장이 잘리나"

소유: 기획 세션. 산출물 design/panel.html
"""
import json, io, os, sys, math

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
from _app import CSS
from _fmt import tier, direct, money, daterange, datesub

D = json.load(io.open(os.path.join(BASE, "..", "docs", "data", "deals.json"), encoding="utf-8"))
deals = D["deals"]
SEL = sorted([d for d in deals if d["o"] == "SEL"], key=lambda x: x["price"])

APP_W, BODY_H = 1200, 640
VB_W, VB_H = 1000, 680          # discover.js:10 고정
ARC_HALF = math.radians(286.7 / 2)   # far 뷰가 담아야 하는 호의 반


def far_scale(stage_w, stage_h=BODY_H):
    """slice 크롭: 종횡비가 vb보다 작으면 가로가 잘린다."""
    f = max(stage_w / float(VB_W), stage_h / float(VB_H))
    vis_w = min(VB_W, stage_w / f)
    return (vis_w / 2.0) / ARC_HALF, vis_w


# ── 문자 폭 근사 (em 단위) ─────────────────────────────────────
# 정확한 값은 폰트가 정하지만, 비교에는 이 정도로 충분하다.
def em(ch):
    o = ord(ch)
    if o >= 0xAC00 or 0x3000 <= o <= 0x9FFF:   # 한글·CJK
        return 1.0
    if ch in "0123456789":
        return 0.58                              # tabular-nums
    if ch in ",.":
        return 0.30
    if ch == " ":
        return 0.28
    if ch in "()":
        return 0.35
    if ch in "→":
        return 0.85
    if ch in "✈":
        return 1.0
    return 0.56


def w(s, px):
    return sum(em(c) for c in s) * px


ROOT = 16
CITY_PX = 0.98 * ROOT      # .fcity
PRICE_PX = 1.18 * ROOT     # .price
BADGE_PX = 0.60 * ROOT     # .bdg
STAMP_PX = 0.60 * ROOT     # .stamp (t2 기준)
DATE_PX = 0.76 * ROOT      # .dmain

# 카드 본문 폭 = 패널 - 좌우 패딩(20) - 카드 패딩(20) - 테두리(3) - 썸네일(62) - 간격(11)
def body_w(panel):
    return panel - 20 - 20 - 3 - 62 - 11


def stamp_w(d):
    t = tier(d)
    if not t:
        return 0
    txt = "%d%%↓" % d["discount"]
    pad = {"t1": 12, "t2": 16, "t3": 18}[t]
    return w(txt, STAMP_PX) + pad + 8      # + gap


def city_row_w(d):
    return w(d["ko"], CITY_PX) + stamp_w(d)


def price_row_w(d):
    x = w(money(d["price"]) + "원", PRICE_PX)
    if direct(d):
        x += w("✈ 직항", BADGE_PX) + 20 + 8
    return x


def date_row_w(d):
    txt = daterange(d.get("dep"), d.get("ret"))
    for a, b in (("<span class=\"wd\">", ""), ("</span>", ""),
                 ("<span class=\"arw\">", ""), ("&rarr;", "→")):
        txt = txt.replace(a, b)
    return w(txt, DATE_PX)


WIDTHS = [320, 360, 380, 420, 460]
rows = []
for pw in WIDTHS:
    bw = body_w(pw)
    stage = APP_W - pw
    sc, vis = far_scale(stage)
    # ⚠️ 처음엔 "몇 장이 잘리나"로 쟀는데 320px에서도 0건이었다.
    #    글자가 잘리는 건 제약이 아니었다 — 대신 "가장 긴 줄이 본문을 얼마나 채우나"로 잰다.
    longest = max(max(city_row_w(d), price_row_w(d), date_row_w(d)) for d in deals)
    rows.append(dict(pw=pw, bw=int(bw), stage=stage, scale=int(sc), vis=int(vis),
                     fill=100.0 * longest / bw, longest=int(longest),
                     cut=sum(1 for d in deals
                             if max(city_row_w(d), price_row_w(d), date_row_w(d)) > bw)))

base = next(r for r in rows if r["pw"] == 380)

# 가장 긴 문자열 (근거로 보여준다)
longest_city = max(deals, key=city_row_w)
longest_price = max(deals, key=price_row_w)

EXTRA = """
.wrapP{max-width:1180px;margin:0 auto;padding:44px 26px 90px}
.strip{display:flex;gap:14px;flex-wrap:wrap;align-items:flex-start;margin:14px 0 30px}
.pcol{border:1px solid #cfdad7;border-radius:13px;overflow:hidden;background:var(--sea)}
.phd{background:#fff;border-bottom:1px solid var(--line);padding:9px 11px}
.phd b{font-size:.92rem;letter-spacing:-.02em}
.phd .sub{font-size:.66rem;color:var(--sub);font-weight:700;margin-top:2px}
.pbody{padding:9px}
.mini{display:flex;flex-direction:column;gap:8px}
.fcard{display:flex;gap:11px;background:#fff;border:1.5px solid var(--line);
 border-radius:13px;padding:10px;overflow:hidden}
.thumb{flex:none;width:62px;height:62px;border-radius:10px;
 background:linear-gradient(140deg,#cfe0dc,#e9efed)}
.fbody{flex:1;min-width:0}
.frow{display:flex;justify-content:space-between;align-items:center;gap:6px}
.fcity{font-size:.98rem;font-weight:900;letter-spacing:-.02em;white-space:nowrap;
 overflow:hidden;text-overflow:ellipsis}
.prow{display:flex;justify-content:space-between;align-items:center;gap:8px;margin-top:2px}
.price{font-weight:900;font-size:1.18rem;letter-spacing:-.03em;font-variant-numeric:tabular-nums;
 white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.price small{font-size:.6em;font-weight:700;color:var(--sub);margin-left:2px}
.dmain{font-size:.76rem;margin-top:5px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.dsub{font-size:.64rem;margin-top:2px}
.bdg{font-size:.6rem;font-weight:800;border-radius:99px;padding:2px 9px;flex:none;
 background:var(--coast);color:#fff;white-space:nowrap}
.stamp{flex:none;font-weight:900;white-space:nowrap;border-radius:4px}
.stamp.t1{transform:rotate(-7deg);border:1.5px solid var(--accent);color:var(--accent);
 font-size:.54rem;padding:1px 5px;background:#fff}
.stamp.t2{transform:rotate(-8deg);background:var(--accent);color:#fff;font-size:.6rem;padding:2px 7px}
.stamp.t3{transform:rotate(-9deg);background:linear-gradient(135deg,#F2603F,#FF8A63 42%,#C6472A);
 color:#fff;font-size:.62rem;padding:2px 8px;box-shadow:0 0 0 2px #fff}
.globe{margin-top:10px;background:#fff;border:1px solid var(--line);border-radius:10px;
 padding:10px;display:flex;flex-direction:column;align-items:center;gap:6px}
.gcirc{border-radius:99px;background:radial-gradient(circle at 34% 32%,#DCE6E3,#B9CFCA);
 border:1px solid #cfdad7}
.gtxt{font-size:.68rem;font-weight:800;color:var(--sub);font-variant-numeric:tabular-nums}
.gtxt b{color:var(--ink);font-size:.86rem}
.delta{font-size:.66rem;font-weight:800;font-variant-numeric:tabular-nums}
.up{color:#1E7A50}.down{color:var(--accent)}.zero{color:var(--sub)}
"""


def mini_card(d, bw):
    t = tier(d)
    stamp = ('<span class="stamp %s">%d%%&darr;</span>' % (t, d["discount"])) if t else ""
    bdg = '<span class="bdg">&#9992; 직항</span>' if direct(d) else ""
    return ('<div class="fcard"><div class="thumb"></div><div class="fbody">'
            '<div class="frow"><span class="fcity">%s</span>%s</div>'
            '<div class="prow"><span class="price">%s<small>원</small></span>%s</div>'
            '<div class="dmain">%s</div><div class="dsub">%s</div></div></div>'
            % (d["ko"], stamp, money(d["price"]), bdg,
               daterange(d.get("dep"), d.get("ret")), datesub(d)))


# 보여줄 카드 — 가장 긴 것들을 섞어 최악을 드러낸다
SHOW = [longest_city, longest_price] + [d for d in SEL[:3]
                                        if d is not longest_city and d is not longest_price]
SHOW = SHOW[:4]

strip = ""
for r in rows:
    d_scale = r["scale"] - base["scale"]
    pct = 100.0 * d_scale / base["scale"]
    cls = "up" if d_scale > 0 else ("down" if d_scale < 0 else "zero")
    sign = "+" if d_scale > 0 else ""
    gsize = int(64 * r["scale"] / float(base["scale"]))
    cutcls = "down" if r["fill"] > 70 else "up"
    strip += ('<div class="pcol" style="width:%dpx">'
              '<div class="phd"><b>%dpx</b>%s'
              '<div class="sub">본문 %dpx · 지도 %dpx</div></div>'
              '<div class="pbody"><div class="mini">%s</div>'
              '<div class="globe"><div class="gcirc" style="width:%dpx;height:%dpx"></div>'
              '<div class="gtxt">far 배율 <b>%d</b> '
              '<span class="delta %s">%s%.1f%%</span></div>'
              '<div class="gtxt %s">가장 긴 줄이 <b>%.0f%%</b> 채움</div></div>'
              '</div></div>'
              % (r["pw"], r["pw"],
                 ' <span style="font-size:.6rem;font-weight:900;background:var(--ink);'
                 'color:#fff;border-radius:4px;padding:2px 6px;vertical-align:2px">지금</span>'
                 if r["pw"] == 380 else
                 (' <span style="font-size:.6rem;font-weight:900;background:var(--accent);'
                  'color:#fff;border-radius:4px;padding:2px 6px;vertical-align:2px">추천</span>'
                  if r["pw"] == 420 else ''),
                 r["bw"], r["stage"],
                 "".join(mini_card(d, r["bw"]) for d in SHOW),
                 gsize, gsize, r["scale"], cls, sign, pct,
                 ("down" if r["fill"] > 70 else "up"), r["fill"]))

trs = ""
for r in rows:
    d_scale = r["scale"] - base["scale"]
    pct = 100.0 * d_scale / base["scale"]
    dw = r["bw"] - base["bw"]
    wpct = 100.0 * dw / base["bw"]
    mark = "win" if r["pw"] == 420 else ""
    trs += ('<tr><td class="k %s">%dpx%s</td>'
            '<td class="num">%d</td><td class="num">%d</td>'
            '<td class="num %s">%s%.1f%%</td>'
            '<td class="num">%d</td><td class="num %s">%s%.1f%%</td>'
            '<td class="num %s">%.0f%%</td></tr>'
            % (mark, r["pw"], " (지금)" if r["pw"] == 380 else "",
               r["stage"], r["scale"],
               "up" if d_scale > 0 else ("down" if d_scale < 0 else "zero"),
               "+" if d_scale > 0 else "", pct,
               r["bw"], "up" if dw > 0 else ("down" if dw < 0 else "zero"),
               "+" if dw > 0 else "", wpct,
               "down" if r["fill"] > 70 else "up", r["fill"]))

html = ("<!doctype html><html lang=ko><head><meta charset=utf-8>"
        "<meta name=viewport content='width=device-width,initial-scale=1'>"
        "<title>갈래말래 — 패널 폭</title><style>" + CSS + EXTRA +
        "</style></head><body><div class=wrapP>"
        "<h1>패널 폭 &mdash; <em>지구냐 카드냐</em></h1>"
        "<p class=lede>좁히면 지도가 넓어져 <b>지구가 커지고</b>, 넓히면 <b>카드가 여유로워진다</b>. "
        "둘 다 실측으로 쟀다 &mdash; 지도는 <code>viewBox 1000&times;680</code> 고정에서 나오는 "
        "far 배율, 카드는 <b>실제 도시명·가격 문자열 폭</b>이다. 앱 폭 " + str(APP_W) + "px 기준.</p>"
        "<div class=strip>" + strip + "</div>"
        "<h2><span class=n>01</span>숫자</h2>"
        "<table><tr><th>패널</th><th style='text-align:right'>지도 폭</th>"
        "<th style='text-align:right'>far 배율</th><th style='text-align:right'>지구 크기</th>"
        "<th style='text-align:right'>카드 본문</th><th style='text-align:right'>카드 폭</th>"
        "<th style='text-align:right'>가장 긴 줄</th></tr>" + trs + "</table>"
        "<h2><span class=n>02</span>내 가설이 틀렸다</h2>"
        "<div class=callout><b>&ldquo;좁히면 글자가 잘린다&rdquo;고 예상했는데 아니었다.</b><br>"
        "<b>320px에서도 잘리는 카드가 0건</b>이다. 가장 긴 줄이 "
        + str(rows[0]["longest"]) + "px인데 본문이 " + str(rows[0]["bw"]) + "px이라 아직 남는다. "
        "도시명이 길어야 <b>" + longest_city["ko"] + "</b>(여섯 자)이고 가격은 아홉 자리가 최대라 "
        "<b>한글 서비스는 애초에 글자가 짧다.</b><br>"
        "그래서 <b>다른 걸 재야 했다</b> &mdash; 잘리느냐가 아니라 "
        "<b>가장 긴 줄이 본문을 얼마나 채우나</b>다.</div>"
        "<ul class=k>"
        "<li><b>320px은 74%를 채운다.</b> 안 잘리지만 오른쪽에 도장이 붙으면 빡빡하다. "
        "<b>380px은 57%</b>라 여유가 있다.</li>"
        "<li><b>좁혀서 얻는 게 적다.</b> 60px을 좁혀도(380&rarr;320) 지구는 <b>+7%</b>뿐이다. "
        "<code>slice</code> 크롭 때문에 <b>무대가 넓어져도 보이는 viewBox 가로는 그만큼 안 늘어난다.</b></li>"
        "<li><b>넓히는 것도 이득이 적다.</b> 420이면 본문은 넉넉해지지만 "
        "<b>어차피 채울 글자가 없다</b> &mdash; 빈 여백만 는다.</li>"
        "<li><b>&lsquo;스르륵 이동&rsquo;이 지도 압박을 덜어준다.</b> 상세를 열면 지도가 그 핀으로 "
        "움직이므로 <b>처음부터 다 보일 필요가 줄었다</b>(2026-09-01 확정). "
        "그게 없었다면 지구 크기를 더 지켜야 했다.</li>"
        "<li><b>그래서 결론은 &lsquo;그대로&rsquo;다.</b> 380px은 이미 균형점이다. "
        "바꿀 근거가 데이터에 없다 &mdash; <b>바꾸지 않는 것도 결정</b>이다.</li>"
        "</ul>"
        "<div class=callout style='border-left-color:#2E7D74'>"
        "<b style='color:#2E7D74'>380px 유지.</b> 좁히면 +7% 지구에 빡빡한 카드를 사고, "
        "넓히면 &minus;5% 지구에 빈 여백을 산다. <b>둘 다 남는 장사가 아니다.</b><br>"
        "<b>모바일에서 다시 볼 문제</b>다 &mdash; 390px 폭에서는 패널이 전폭이라 "
        "이 저울이 통째로 달라진다.</div>"
        "<p class=note>&#9888; <b>문자 폭은 근사다.</b> 정확한 값은 폰트가 정한다 &mdash; "
        "한글 1.0em · 숫자 0.58em(tabular) 같은 어림으로 쟀다. "
        "<b>순위를 가리는 데는 충분하지만 경계값 근처는 브라우저로 봐야 한다.</b> "
        "이 세션엔 브라우저가 없다.</p>"
        "<p class=foot>생성 <b>design/build_panel.py</b> &middot; 데이터 <b>docs/data/deals.json</b> "
        "&middot; 확정 홈 <b>home.html</b> &middot; 스펙 <b>../SPEC.md</b> &sect;CH1</p>"
        "</div></body></html>")

io.open(os.path.join(BASE, "panel.html"), "w", encoding="utf-8").write(html)
print("panel.html  %.1fKB" % (len(html) / 1024.0))
for r in rows:
    print("  panel %d  stage %d  scale %d  body %d  cut %d"
          % (r["pw"], r["stage"], r["scale"], r["bw"], r["cut"]))
print("  longest city: %s (%.0fpx)" % (longest_city["ko"], city_row_w(longest_city)))
print("  longest price: %s (%.0fpx)" % (money(longest_price["price"]), price_row_w(longest_price)))
