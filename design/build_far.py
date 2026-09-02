# -*- coding: utf-8 -*-
"""'아주 멀리'에서 대륙으로 더 들어가기.

사용자 지적(2026-09-01): "뉴욕 유럽은 상세하게 못 보는데,
아주 멀리에서 대륙을 선택해서 들어갈 수 있게 하는 건 어떨까?"

실측: far 뷰(배율 174)에서 유럽 10건이 89x58px 안에 들어간다.
소유: 기획 세션. 산출물 design/far.html
"""
import json, io, os, sys, math, collections

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
from _app import CSS
from _fmt import tier, money

D = json.load(io.open(os.path.join(BASE, "..", "docs", "data", "deals.json"), encoding="utf-8"))
SEL = sorted([d for d in D["deals"] if d["o"] == "SEL"], key=lambda x: x["price"])
ORG = D["origins"]["SEL"]

SW, SH = 620, 420          # 목업 무대
KO = {"eu": "유럽", "am": "미주", "oc": "오세아니아", "island": "섬",
      "etc": "그 외", "sea": "동남아", "cn": "중국", "jp": "일본", "dom": "국내"}

LONG = [d for d in SEL if d["haul"] == "long"]
GROUPS = ["eu", "am", "oc"]
rest = [d for d in LONG if d.get("region") not in GROUPS]
gc = collections.Counter(d.get("region") for d in LONG)


def fit(deals, w, h, pad=70):
    """그 딜들을 담는 중심·배율을 계산한다 (§CH1 계산식과 같은 방식)."""
    lons = sorted(d["lon"] for d in deals)
    lats = [d["lat"] for d in deals]
    if len(lons) > 1:
        gaps = [((lons[(i + 1) % len(lons)] - lons[i]) % 360, lons[i], lons[(i + 1) % len(lons)])
                for i in range(len(lons))]
        g, a, b = max(gaps)
        arc = 360 - g
        ctr = ((b + arc / 2.0 + 180) % 360) - 180
    else:
        arc, ctr = 10.0, lons[0]
    lat0 = (min(lats) + max(lats)) / 2.0
    span_lat = max(2.0, max(lats) - min(lats))
    s = min((w - pad * 2) / 2.0 / max(1e-6, math.radians(arc / 2)),
            (h - pad * 2) / 2.0 / max(1e-6, math.radians(span_lat / 2)))
    return ctr, lat0, s


def project(deals, ctr, lat0, s):
    out = []
    for d in deals:
        dl = ((d["lon"] - ctr + 180) % 360) - 180
        out.append((d, SW / 2 + math.radians(dl) * s, SH / 2 - math.radians(d["lat"] - lat0) * s))
    return out


# far 뷰 (현행)
FAR_CTR, FAR_LAT, FAR_S = 142.9, 0.0, 174 * (SW / 1000.0)
far_pts = project(SEL, FAR_CTR, FAR_LAT, FAR_S)

EXTRA = """
.wrapR{max-width:1320px;margin:0 auto;padding:44px 26px 90px}
.grid{display:flex;gap:18px;flex-wrap:wrap;margin:16px 0 30px}
.gc{width:620px}
.ghd{display:flex;align-items:baseline;gap:8px}
.gid{font-size:.64rem;font-weight:900;background:var(--ink);color:#fff;border-radius:4px;padding:2px 7px}
.gnm{font-weight:800;font-size:.92rem}
.rec{font-size:.55rem;font-weight:900;background:var(--accent);color:#fff;border-radius:4px;padding:2px 6px;vertical-align:2px}
.no{font-size:.55rem;font-weight:900;background:var(--sub);color:#fff;border-radius:4px;padding:2px 6px;vertical-align:2px}
.gdesc{color:var(--sub);font-size:.78rem;line-height:1.62;min-height:60px;margin:5px 0 9px}
.stg{width:620px;height:420px;position:relative;background:var(--sea);
 border:1px solid #cfdad7;border-radius:13px;overflow:hidden}
.land{position:absolute;background:var(--land);border-radius:44% 56% 38% 62%/52% 42% 58% 48%}
.pin{position:absolute;border-radius:99px;background:var(--accent);z-index:2}
.pin.maj{width:11px;height:11px;margin:-5.5px 0 0 -5.5px;box-shadow:0 0 0 3px rgba(242,96,63,.18)}
.pin.min{width:5px;height:5px;margin:-2.5px 0 0 -2.5px;opacity:.5}
.pin.org{background:var(--coast);width:12px;height:12px;margin:-6px 0 0 -6px;
 box-shadow:0 0 0 4px rgba(46,125,116,.2)}
.plab{position:absolute;transform:translate(-50%,-200%);font-size:.6rem;font-weight:800;
 background:#fff;border-radius:4px;padding:1px 6px;white-space:nowrap;box-shadow:0 2px 6px #0002;z-index:4}
.ring{position:absolute;border:2px dashed var(--accent);border-radius:16px;z-index:3;
 background:rgba(242,96,63,.06)}
.rlab{position:absolute;transform:translate(-50%,0);background:var(--accent);color:#fff;
 font-size:.62rem;font-weight:900;border-radius:99px;padding:3px 10px;white-space:nowrap;z-index:5;
 box-shadow:0 2px 8px rgba(242,96,63,.3)}
.sbar{position:absolute;left:12px;top:12px;display:flex;gap:5px;z-index:7}
.sbar2{position:absolute;left:12px;top:48px;display:flex;gap:5px;z-index:7}
.pill{background:#fff;border:1px solid var(--line);border-radius:99px;padding:5px 11px;
 font-size:.68rem;font-weight:800;color:var(--sub);box-shadow:0 2px 8px #0000000f;white-space:nowrap}
.pill.on{background:var(--ink);color:#fff;border-color:var(--ink)}
.pill.sub{border-color:var(--accent);color:var(--accent);background:#FFF6F3}
.pill.sub.on{background:var(--accent);color:#fff}
.pill .n{font-size:.6rem;opacity:.65;margin-left:4px;font-weight:700}
.mt5{display:flex;gap:7px;margin-top:9px}
.mt5 div{flex:1;background:#fff;border:1px solid var(--line);border-radius:9px;padding:7px 8px;
 text-align:center;font-size:.62rem;color:var(--sub);font-weight:700;line-height:1.4}
.mt5 b{display:block;font-size:1.0rem;letter-spacing:-.02em;color:var(--ink)}
.mt5 .g b{color:#1E7A50}.mt5 .r b{color:var(--accent)}
"""

LANDS = "".join('<div class="land" style="left:%dpx;top:%dpx;width:%dpx;height:%dpx"></div>' % g
                for g in [(20, 60, 190, 150), (150, 30, 150, 120), (80, 200, 170, 140),
                          (270, 120, 130, 120), (320, 240, 120, 100), (440, 70, 120, 130),
                          (480, 230, 110, 110)])


def draw(pts, labels=None, rings=(), bars=""):
    out = LANDS
    for d, x, y in pts:
        if not (-20 < x < SW + 20 and -20 < y < SH + 20):
            continue
        cls = "maj" if d.get("tier") == "major" else "min"
        out += '<span class="pin %s" style="left:%.0fpx;top:%.0fpx"></span>' % (cls, x, y)
    if labels:
        for d, x, y in pts:
            if d["ko"] in labels and -20 < x < SW + 20 and -20 < y < SH + 20:
                out += '<span class="plab" style="left:%.0fpx;top:%.0fpx">%s</span>' % (x, y, d["ko"])
    for (l, t, w, h, lab) in rings:
        out += ('<div class="ring" style="left:%.0fpx;top:%.0fpx;width:%.0fpx;height:%.0fpx"></div>'
                '<span class="rlab" style="left:%.0fpx;top:%.0fpx">%s</span>'
                % (l, t, w, h, l + w / 2, t + h + 6, lab))
    return '<div class="stg">' + out + bars + '</div>'


BAR1 = ('<div class="sbar"><span class="pill">가까운 곳</span>'
        '<span class="pill">조금 더 멀리</span><span class="pill on">아주 멀리</span></div>')


def bar2(on=None):
    out = '<div class="sbar2">'
    for k in GROUPS:
        cls = " on" if k == on else ""
        out += ('<span class="pill sub%s">%s<span class="n">%d</span></span>'
                % (cls, KO[k], gc.get(k, 0)))
    out += '<span class="pill sub">그 외<span class="n">%d</span></span></div>' % len(rest)
    return out


# ── G0 현행 ────────────────────────────────────────────────────
G0 = draw(far_pts, labels={"도쿄", "방콕", "뉴욕", "파리"}, bars=BAR1)

# ── 유럽 뷰 (들어갔을 때) ──────────────────────────────────────
eu = [d for d in LONG if d.get("region") == "eu"]
c, la, s = fit(eu, SW, SH)
EU = draw(project(eu, c, la, s), labels={d["ko"] for d in eu},
          bars='<div class="sbar"><span class="pill">&larr; 아주 멀리</span></div>' + bar2("eu"))

am = [d for d in LONG if d.get("region") == "am"]
c2, la2, s2 = fit(am, SW, SH)
AM = draw(project(am, c2, la2, s2), labels={d["ko"] for d in am},
          bars='<div class="sbar"><span class="pill">&larr; 아주 멀리</span></div>' + bar2("am"))

# ── G1 단계바 2단 ─────────────────────────────────────────────
G1 = draw(far_pts, labels={"도쿄", "방콕"}, bars=BAR1 + bar2())

# ── G2 지도에서 묶음 ──────────────────────────────────────────
def bbox(reg):
    p = [(x, y) for d, x, y in far_pts if d.get("region") == reg]
    if not p:
        return None
    xs = [q[0] for q in p]; ys = [q[1] for q in p]
    return (min(xs) - 16, min(ys) - 16, max(xs) - min(xs) + 32, max(ys) - min(ys) + 32)


rings = []
for k in GROUPS:
    b = bbox(k)
    if b:
        rings.append((b[0], b[1], b[2], b[3], "%s %d" % (KO[k], gc.get(k, 0))))
G2 = draw(far_pts, labels={"도쿄", "방콕"}, rings=rings, bars=BAR1)

eu_w = max(x for d, x, y in far_pts if d.get("region") == "eu") - \
       min(x for d, x, y in far_pts if d.get("region") == "eu")

OPTS = [
    ("G0", "지금 — 한 화면에 전부", "현행", "no", G0,
     "유럽 10건이 <b>가로 %.0fpx</b> 안에 들어간다. 런던 65 · 파리 74로 <b>9px 차이</b>이고, "
     "취리히와 프랑크푸르트는 <b>같은 점</b>이다. 미주도 밴쿠버·시애틀·샌프란시스코가 "
     "<b>3px 안에 셋</b>이다." % eu_w,
     ["1", "%.0fpx" % eu_w, "×"]),
    ("G1", "단계바 두 번째 줄", "추천", "rec", G1,
     "<code>아주 멀리</code>를 고르면 <b>그때만</b> 대륙 줄이 나타난다. "
     "평소엔 없으므로 <b>영구 UI가 안 는다.</b><br>"
     "거리 축이 끝나는 지점에서 <b>방향 축</b>이 시작된다 &mdash; 같은 모델의 연장이다.",
     ["2", "6~10배", "○"]),
    ("G2", "지도에서 묶음 누르기", "", "", G2,
     "뭉친 지역에 <b>점선 테두리와 이름표</b>를 씌운다. 누르면 그 대륙으로 간다.<br>"
     "<b>공간적이라 발견에 어울린다.</b> 다만 핀 위에 <b>레이어가 하나 더</b> 얹히고, "
     "테두리가 개별 핀을 가린다.",
     ["1", "6~10배", "○"]),
]

cards = ""
for gid, nm, badge, cls, mk, desc, mt in OPTS:
    b = ('<span class="rec">%s</span>' % badge if cls == "rec"
         else '<span class="no">%s</span>' % badge if badge else "")
    m = '<div class="mt5">'
    for i, v in enumerate(mt):
        k = "r" if v in ("×",) else ("g" if v in ("○",) else "")
        m += '<div class="%s"><b>%s</b>%s</div>' % (k, v, ["단계바 줄", "유럽 배율", "유럽을 볼 수 있나"][i])
    m += '</div>'
    cards += ('<div class="gc"><div class="ghd"><span class="gid">%s</span>'
              '<span class="gnm">%s</span>%s</div><div class="gdesc">%s</div>%s%s</div>'
              % (gid, nm, b, desc, mk, m))

grp = "".join('<tr><td class="k">%s</td><td class="num">%d건</td><td>%s</td></tr>'
              % (KO[k], gc.get(k, 0), " · ".join(d["ko"] for d in LONG if d.get("region") == k))
              for k in GROUPS) + \
      '<tr><td class="k">그 외</td><td class="num">%d건</td><td>%s</td></tr>' \
      % (len(rest), " · ".join(d["ko"] for d in rest))

html = ("<!doctype html><html lang=ko><head><meta charset=utf-8>"
        "<meta name=viewport content='width=device-width,initial-scale=1'>"
        "<title>갈래말래 — 아주 멀리에서 대륙으로</title><style>" + CSS + EXTRA +
        "</style></head><body><div class=wrapR>"
        "<h1>&lsquo;아주 멀리&rsquo;에서 <em>대륙으로</em></h1>"
        "<p class=lede><b>지적이 맞았고 생각보다 심하다.</b> far 뷰(배율 174)에서 "
        "<b>유럽 10건이 가로 " + ("%.0f" % eu_w) + "px</b> 안에 들어간다. "
        "서울 출발 실제 좌표로 그렸다.</p>"
        "<div class=callout><b>거리 축이 끝나는 곳에서 방향 축이 시작된다.</b><br>"
        "단계 셋은 <b>거리</b>로 나뉜다. 그런데 유럽과 미주는 <b>둘 다 &lsquo;아주 멀리&rsquo;</b>이고 "
        "<b>더 갈 데가 없다.</b> 거기서는 거리가 더 이상 쓸모 있는 축이 아니다.<br>"
        "→ <b>단계 버튼이 못 하는 일</b>이라, 대륙 선택이 <b>같은 일을 두 번 하는 게 아니다.</b> "
        "(가까운 쪽 뭉침은 단계 버튼이 이미 해결한다.)</div>"
        "<h2><span class=n>01</span>후보</h2>"
        "<div class=grid>" + cards + "</div>"
        "<h2><span class=n>02</span>들어가면 이렇게 보인다</h2>"
        "<p class=note>같은 계산식(경도 정렬 → 최대 빈 구간 → 중심)을 그 대륙 딜에만 적용한다. "
        "<b>새 규칙이 아니라 같은 규칙을 좁은 집합에 쓰는 것</b>이다.</p>"
        "<div class=grid>"
        "<div class=gc><div class=ghd><span class=gid>유럽</span>"
        "<span class=gnm>배율 " + str(int(s)) + " &mdash; far의 " + ("%.1f" % (s / FAR_S)) + "배</span></div>"
        "<div class=gdesc>10건이 화면 전체에 퍼진다. 런던·파리·바르셀로나가 구별된다.</div>" + EU + "</div>"
        "<div class=gc><div class=ghd><span class=gid>미주</span>"
        "<span class=gnm>배율 " + str(int(s2)) + " &mdash; far의 " + ("%.1f" % (s2 / FAR_S)) + "배</span></div>"
        "<div class=gdesc>밴쿠버·시애틀·샌프란시스코가 갈라진다. far에선 3px 안에 셋이었다.</div>" + AM + "</div>"
        "</div>"
        "<h2><span class=n>03</span>그룹</h2>"
        "<table style='max-width:900px'><tr><th style='width:100px'>대륙</th>"
        "<th style='text-align:right;width:70px'>딜</th><th>목적지</th></tr>" + grp + "</table>"
        "<h2><span class=n>왜</span>G1</h2>"
        "<ul class=k>"
        "<li><b>평소엔 안 보인다.</b> <code>아주 멀리</code>를 고른 뒤에만 두 번째 줄이 뜬다 &mdash; "
        "가까운 단계에서 대륙 칩이 보이면 혼란스럽다.</li>"
        "<li><b>피드도 같이 걸러진다.</b> 현행 <code>visibleCities()</code>가 이미 그렇다 &mdash; "
        "단계가 지도와 피드를 <b>같이</b> 거른다. 대륙도 같은 규칙이면 <b>새로 배울 게 없다.</b></li>"
        "<li><b>계산식이 같다.</b> 경도 정렬 → 최대 빈 구간 → 그 정반대가 중심. "
        "<b>같은 함수를 좁은 집합에 부르면 끝</b>이다(프론트가 이미 함수로 바꾸는 중).</li>"
        "<li><b>G2는 매력적이지만 레이어가 는다.</b> 우리는 방금 &lsquo;핀은 숨기지 않고 낮춘다&rsquo;로 "
        "표현을 정리했는데, 그 위에 테두리를 또 얹으면 <b>지도 언어가 셋</b>이 된다.</li>"
        "<li>⚠️ <b>돌아오는 길이 필요하다.</b> 단계바 첫 줄이 <code>&larr; 아주 멀리</code>로 바뀐다.</li>"
        "</ul>"
        "<p class=note>&#9888; <b>&lsquo;그 외&rsquo; " + str(len(rest)) + "건</b>(" +
        " · ".join(d["ko"] for d in rest) + ")은 서로 멀어 한 화면에 안 담긴다. "
        "<b>대륙이 아니라 &lsquo;나머지 전부&rsquo;</b>라 far 뷰와 같게 보일 수 있다 &mdash; "
        "칩을 아예 안 두는 것도 방법이다. 사용자 판단.</p>"
        "<p class=foot>생성 <b>design/build_far.py</b> &middot; 데이터 <b>docs/data/deals.json</b>"
        "(서울 " + str(len(SEL)) + "건, 장거리 " + str(len(LONG)) + "건) &middot; "
        "핀 밀도 <b>pins.html</b> &middot; 단계 <b>stages.html</b></p>"
        "</div></body></html>")

io.open(os.path.join(BASE, "far.html"), "w", encoding="utf-8").write(html)
print("far.html  %.1fKB" % (len(html) / 1024.0))
print("  long %d = eu %d · am %d · oc %d · rest %d" % (len(LONG), gc.get("eu", 0), gc.get("am", 0), gc.get("oc", 0), len(rest)))
print("  유럽 far 가로폭 %.0fpx -> 대륙뷰 배율 %.0f (%.1f배)" % (eu_w, s, s / FAR_S))
print("  미주 대륙뷰 배율 %.0f (%.1f배)" % (s2, s2 / FAR_S))
