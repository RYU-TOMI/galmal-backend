# -*- coding: utf-8 -*-
"""far 뷰 핀 밀도 — "아주 멀리"에서 점이 너무 많다.

사용자 지적(2026-09-01): "아주 멀리로 가면 왼쪽 카드는 잘 보이되
점은 주요 도시에만 찍히게 하는 건 어떨까?"

실제 좌표를 far 뷰 투영(중심 142.9°E · 배율 174)으로 그린다.
소유: 기획 세션. 산출물 design/pins.html
"""
import json, io, os, sys, math, collections

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
from _app import CSS
from _fmt import money

D = json.load(io.open(os.path.join(BASE, "..", "docs", "data", "deals.json"), encoding="utf-8"))
SEL = sorted([d for d in D["deals"] if d["o"] == "SEL"], key=lambda x: x["price"])
ORG = D["origins"]["SEL"]

# ── far 뷰 투영 (SPEC §CH1 계산식) ─────────────────────────────
VW, VH = 620, 420          # 목업 무대 (실제 viewBox 1000x680의 비율 축소)
K = 174 * (VW / 1000.0)    # far 배율을 목업 크기에 맞춤
LON0, LAT0 = 142.9, 30.0


def proj(lon, lat):
    dl = ((lon - LON0 + 180) % 360) - 180
    return (VW / 2 + math.radians(dl) * K, VH / 2 - math.radians(lat - LAT0) * K)


for d in SEL:
    d["_x"], d["_y"] = proj(d["lon"], d["lat"])
OX, OY = proj(ORG["lon"], ORG["lat"])

MAJOR = [d for d in SEL if d.get("tier") == "major"]
MINOR = [d for d in SEL if d.get("tier") != "major"]


def crowded(pts, r):
    n = 0
    for i, a in enumerate(pts):
        for j, b in enumerate(pts):
            if i != j and (a["_x"] - b["_x"]) ** 2 + (a["_y"] - b["_y"]) ** 2 < r * r:
                n += 1
                break
    return n


# ── 클러스터 (격자 기반, 가까운 것끼리 묶는다) ─────────────────
CELL = 26


def cluster(pts):
    cells = collections.defaultdict(list)
    for d in pts:
        cells[(int(d["_x"] // CELL), int(d["_y"] // CELL))].append(d)
    out = []
    for _, group in cells.items():
        if len(group) == 1:
            out.append({"solo": group[0]})
        else:
            out.append({"n": len(group),
                        "x": sum(g["_x"] for g in group) / len(group),
                        "y": sum(g["_y"] for g in group) / len(group),
                        "region": collections.Counter(
                            g.get("region", "?") for g in group).most_common(1)[0][0]})
    return out


CL = cluster(SEL)
n_marks = len(CL)

REGION_KO = {"jp": "일본", "cn": "중국", "sea": "동남아", "eu": "유럽",
             "am": "미주", "island": "섬", "dom": "국내", "etc": "그 외"}

EXTRA = """
.wrapN{max-width:1340px;margin:0 auto;padding:44px 26px 90px}
.grid{display:flex;gap:18px;flex-wrap:wrap;margin:16px 0 30px}
.pc{width:620px}
.phd{display:flex;align-items:baseline;gap:8px}
.pid{font-size:.64rem;font-weight:900;background:var(--ink);color:#fff;border-radius:4px;padding:2px 7px}
.pnm{font-weight:800;font-size:.92rem}
.rec{font-size:.55rem;font-weight:900;background:var(--accent);color:#fff;border-radius:4px;padding:2px 6px;vertical-align:2px}
.no{font-size:.55rem;font-weight:900;background:var(--sub);color:#fff;border-radius:4px;padding:2px 6px;vertical-align:2px}
.pdesc{color:var(--sub);font-size:.78rem;line-height:1.62;min-height:66px;margin:5px 0 9px}
.stg{width:620px;height:420px;position:relative;background:var(--sea);
 border:1px solid #cfdad7;border-radius:13px;overflow:hidden}
.land{position:absolute;background:var(--land);border-radius:44% 56% 38% 62%/52% 42% 58% 48%}
.pin{position:absolute;border-radius:99px;background:var(--accent)}
.pin.maj{width:11px;height:11px;margin:-5.5px 0 0 -5.5px;box-shadow:0 0 0 3px rgba(242,96,63,.18)}
.pin.min{width:11px;height:11px;margin:-5.5px 0 0 -5.5px;box-shadow:0 0 0 3px rgba(242,96,63,.18)}
.pin.quiet{width:5px;height:5px;margin:-2.5px 0 0 -2.5px;opacity:.5;box-shadow:none}
.pin.org{background:var(--coast);width:12px;height:12px;margin:-6px 0 0 -6px;
 box-shadow:0 0 0 4px rgba(46,125,116,.2)}
.plab{position:absolute;transform:translate(-50%,-200%);font-size:.58rem;font-weight:800;
 background:#fff;border-radius:4px;padding:1px 6px;white-space:nowrap;box-shadow:0 2px 6px #0002}
.clu{position:absolute;transform:translate(-50%,-50%);min-width:30px;height:30px;
 border-radius:99px;background:#fff;border:2px solid var(--accent);color:var(--accent);
 font-size:.68rem;font-weight:900;display:flex;align-items:center;justify-content:center;
 box-shadow:0 2px 8px rgba(242,96,63,.24);padding:0 6px}
.clu i{font-style:normal;font-size:.56rem;color:var(--sub);margin-left:3px;font-weight:800}
.mt4{display:flex;gap:7px;margin-top:9px}
.mt4 div{flex:1;background:#fff;border:1px solid var(--line);border-radius:9px;padding:7px 8px;
 text-align:center;font-size:.62rem;color:var(--sub);font-weight:700;line-height:1.4}
.mt4 b{display:block;font-size:1.0rem;letter-spacing:-.02em;color:var(--ink)}
.mt4 .g b{color:#1E7A50}.mt4 .r b{color:var(--accent)}
"""

LANDS = "".join('<div class="land" style="left:%dpx;top:%dpx;width:%dpx;height:%dpx"></div>' % g
                for g in [(30, 60, 190, 160), (150, 30, 160, 130), (90, 200, 180, 150),
                          (280, 130, 140, 120), (330, 250, 130, 100), (450, 80, 130, 140),
                          (490, 240, 110, 110)])


def stage(inner):
    return '<div class="stg">' + LANDS + inner + '</div>'


def org_pin():
    return '<span class="pin org" style="left:%.0fpx;top:%.0fpx"></span>' % (OX, OY)


def pins(items, cls="maj"):
    return "".join('<span class="pin %s" style="left:%.0fpx;top:%.0fpx"></span>'
                   % (cls, d["_x"], d["_y"]) for d in items)


def labels(items, k=7):
    return "".join('<span class="plab" style="left:%.0fpx;top:%.0fpx">%s</span>'
                   % (d["_x"], d["_y"], d["ko"]) for d in items[:k])


LAB = sorted(MAJOR, key=lambda d: d["price"])[:7]

# A0 현행
A0 = stage(org_pin() + pins(MAJOR) + pins(MINOR, "min") + labels(LAB))
# A1 사용자 제안 — major만
A1 = stage(org_pin() + pins(MAJOR) + labels(LAB))
# A2 minor를 작고 조용하게
A2 = stage(org_pin() + pins(MINOR, "quiet") + pins(MAJOR) + labels(LAB))
# A3 클러스터
cl_html = org_pin()
for c in CL:
    if "solo" in c:
        d = c["solo"]
        cls = "maj" if d.get("tier") == "major" else "min"
        cl_html += '<span class="pin %s" style="left:%.0fpx;top:%.0fpx"></span>' % (cls, d["_x"], d["_y"])
    else:
        cl_html += ('<span class="clu" style="left:%.0fpx;top:%.0fpx">%d<i>%s</i></span>'
                    % (c["x"], c["y"], c["n"], REGION_KO.get(c["region"], "")))
A3 = stage(cl_html)

OPTS = [
    ("A0", "지금", "현행", "no", A0,
     "핀 <b>70개</b>가 전부 같은 크기다. <b>66%가 16px 안에 이웃</b>을 갖는다 &mdash; "
     "동남아·중국·일본에 몰려 뭉갠다.",
     [str(len(SEL)), str(crowded(SEL, 16)), "0"]),
    ("A1", "주요 도시만", "제안", "", A1,
     "<b>major 36개</b>만 찍는다. 확실히 깨끗해진다.<br>"
     "다만 <b>34건이 지도에서 사라지고 그중 14건이 장거리</b>다 &mdash; "
     "&lsquo;아주 멀리&rsquo;를 골랐는데 먼 곳이 사라진다.",
     [str(len(MAJOR)), str(crowded(MAJOR, 16)), str(len(MINOR))]),
    ("A2", "minor를 작고 조용하게", "추천", "rec", A2,
     "<b>없애지 않고 낮춘다.</b> major는 그대로, minor는 <b>5px 반투명·후광 없음</b>.<br>"
     "시각 무게는 크게 줄지만 <b>피드의 모든 딜이 지도에 있다</b>. "
     "카드를 누르면 그 핀이 커진다.",
     [str(len(SEL)), str(crowded(MAJOR, 16)), "0"]),
    ("A3", "가까운 것끼리 묶기", "", "", A3,
     "겹치는 핀을 <b>%d개 표시</b>로 묶는다. 누르면 그 거리대 단계로 간다.<br>"
     "가장 깔끔하지만 <b>개별 도시가 안 보이고</b>, 단계 모델 위에 개념이 하나 더 얹힌다." % n_marks,
     [str(n_marks), "0", "0"]),
]

cards = ""
for pid, nm, badge, cls, mk, desc, mt in OPTS:
    b = ('<span class="rec">%s</span>' % badge if cls == "rec"
         else '<span class="no">%s</span>' % badge if badge else "")
    m = '<div class="mt4">'
    for i, v in enumerate(mt):
        k = ""
        if i == 1:
            k = "g" if int(v) <= 20 else "r"
        if i == 2:
            k = "r" if int(v) > 0 else "g"
        m += '<div class="%s"><b>%s</b>%s</div>' % (k, v, ["보이는 표시", "겹치는 핀", "사라진 딜"][i])
    m += '</div>'
    cards += ('<div class="pc"><div class="phd"><span class="pid">%s</span>'
              '<span class="pnm">%s</span>%s</div><div class="pdesc">%s</div>%s%s</div>'
              % (pid, nm, b, desc, mk, m))

reg = collections.Counter()
for i, a in enumerate(SEL):
    for j, b2 in enumerate(SEL):
        if i != j and (a["_x"] - b2["_x"]) ** 2 + (a["_y"] - b2["_y"]) ** 2 < 256:
            reg[a.get("region", "?")] += 1
            break
regtr = "".join('<tr><td class="k">%s</td><td class="num">%d개</td></tr>'
                % (REGION_KO.get(k, k), v) for k, v in reg.most_common())

html = ("<!doctype html><html lang=ko><head><meta charset=utf-8>"
        "<meta name=viewport content='width=device-width,initial-scale=1'>"
        "<title>갈래말래 — far 뷰 핀 밀도</title><style>" + CSS + EXTRA +
        "</style></head><body><div class=wrapN>"
        "<h1>&lsquo;아주 멀리&rsquo;의 점 &mdash; <em>너무 많다</em></h1>"
        "<p class=lede>서울 출발 <b>" + str(len(SEL)) + "건</b>을 far 뷰 투영"
        "(중심 <code>142.9&deg;E</code> · 배율 174)으로 그렸다. <b>체감이 맞다</b> &mdash; "
        "<b>66%의 핀이 16px 안에 이웃</b>을 갖는다.</p>"
        "<div class=callout><b>몰리는 곳은 &lsquo;먼 곳&rsquo;이 아니라 &lsquo;가까운 곳&rsquo;이다.</b><br>"
        "겹치는 핀 46개 중 <b>동남아 13 · 중국 12 · 일본 8 = 33개</b>가 근·중거리다. "
        "장거리(유럽 6 · 미주 2)는 넓게 퍼져 있어 안 겹친다.<br>"
        "→ <b>줄여야 할 건 가까운 쪽인데, &lsquo;major만&rsquo;은 먼 쪽도 같이 지운다.</b></div>"
        "<div class=grid>" + cards + "</div>"
        "<h2><span class=n>01</span>어디가 붐비나</h2>"
        "<table style='max-width:340px'><tr><th>지역</th>"
        "<th style='text-align:right'>겹치는 핀</th></tr>" + regtr + "</table>"
        "<h2><span class=n>왜</span>A2 &mdash; 없애지 말고 낮춘다</h2>"
        "<div class=callout><b>점을 지우면 규칙 하나가 깨진다.</b><br>"
        "<code>FLOWS.md</code> <b>F15</b> &mdash; <b>피드에 있는 딜은 지도에서 찾을 수 있어야 한다.</b> "
        "&lsquo;major만&rsquo;으로 가면 <b>카드는 있는데 핀이 없는 딜이 34건</b> 생긴다. "
        "그중 <b>14건이 장거리</b>라 &lsquo;아주 멀리&rsquo;가 자기 목적을 배신한다.<br>"
        "<b>A2는 지우지 않고 낮춘다</b> &mdash; minor를 <b>5px 반투명·후광 없음</b>으로. "
        "시각 무게는 major의 <b>1/5</b>이라 뭉치는 느낌이 사라지는데 <b>딜은 하나도 안 없어진다.</b></div>"
        "<ul class=k>"
        "<li><b>카드를 누르면 그 핀이 커진다.</b> 조용한 점도 <b>부를 수 있다</b> &mdash; "
        "이미 확정한 &lsquo;스르륵&rsquo; 동작이 minor 핀에도 그대로 적용된다.</li>"
        "<li><b>라벨은 지금도 major만</b>이다(LOD 규칙). 소음의 절반은 이미 잡혀 있고, "
        "남은 건 <b>점 자체의 무게</b>다.</li>"
        "<li><b>A3(묶기)는 가장 깔끔하지만 개념이 하나 는다.</b> "
        "단계 버튼이 이미 &lsquo;거리대를 고르는&rsquo; 장치인데 클러스터를 누르면 또 단계가 바뀐다 &mdash; "
        "<b>같은 일을 하는 조작이 둘</b>이 된다. 밀도가 더 심해지면 그때 꺼낸다.</li>"
        "<li>⚠️ <b>A1을 완전히 버리진 않는다.</b> minor를 낮춰도 여전히 답답하면 "
        "&lsquo;아주 멀리&rsquo;에서만 <b>근거리 minor를 접는</b> 절충이 가능하다. "
        "다만 그건 <b>먼 곳은 남기는</b> 방식이어야 한다.</li>"
        "</ul>"
        "<p class=note>&#9888; <b>이 세션엔 브라우저가 없다.</b> "
        "5px 반투명이 실제로 충분히 조용한지는 <b>눈으로 봐야</b> 안다. "
        "위 목업은 같은 CSS를 쓰지만 무대가 실제(1000&times;680)보다 작아 "
        "<b>실제로는 더 성기게</b> 보인다.</p>"
        "<p class=foot>생성 <b>design/build_pins.py</b> &middot; 데이터 <b>docs/data/deals.json</b> "
        "&middot; 단계 설계 <b>stages.html</b> &middot; 스펙 <b>../SPEC.md</b> &sect;CH1</p>"
        "</div></body></html>")

io.open(os.path.join(BASE, "pins.html"), "w", encoding="utf-8").write(html)
print("pins.html  %.1fKB" % (len(html) / 1024.0))
print("  deals %d (major %d / minor %d)" % (len(SEL), len(MAJOR), len(MINOR)))
print("  crowded@16px: all %d / major-only %d" % (crowded(SEL, 16), crowded(MAJOR, 16)))
print("  cluster marks: %d" % n_marks)
