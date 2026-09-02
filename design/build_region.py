# -*- coding: utf-8 -*-
"""대륙 호버 — 게임에서 영토 고르듯 (방법 A: 좌표로 추정).

사용자 제안(2026-09-01): "게임에서 땅 선택하듯이 호버하면 대륙 모양으로 살짝 뜨고
그쪽이 선택되는 느낌."

world.geojson에 속성이 없어(182개 전부 `{}`) 나라를 식별할 수 없다.
→ 각 육지 조각의 **중심 좌표**를 계산해 지역 bbox에 넣는다. 속성 없이도 된다.

확대는 CSS transform 한 번이다 — 등거리원통도법이 경위도에 선형이라
center·scale 변경이 평면 아핀변환이 된다(프론트 CH1 T5와 같은 원리).

소유: 기획 세션. 산출물 design/region.html
"""
import json, io, os, sys, math, collections

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
from _app import CSS
from _fmt import tier, money

D = json.load(io.open(os.path.join(BASE, "..", "docs", "data", "deals.json"), encoding="utf-8"))
W = json.load(io.open(os.path.join(BASE, "..", "docs", "data", "world.geojson"), encoding="utf-8"))
SEL = sorted([d for d in D["deals"] if d["o"] == "SEL"], key=lambda x: x["price"])
ORG = D["origins"]["SEL"]

SW, SH = 900, 560
LON0, LAT0 = 142.9, 0.0
K0 = 174 * (SW / 1000.0)          # far 배율을 목업 크기로

KO = {"eu": "유럽", "am": "미주", "oc": "오세아니아",
      "sea": "동남아", "cn": "중국", "jp": "일본", "island": "섬", "etc": "그 외"}
# 「아주 멀리」에서 고를 수 있는 것 — 장거리만
PICK = ["eu", "am", "oc"]


def px(lon, lat, lon_c=LON0, lat_c=LAT0, k=K0):
    dl = ((lon - lon_c + 180) % 360) - 180
    return (SW / 2 + math.radians(dl) * k, SH / 2 - math.radians(lat - lat_c) * k)


for d in SEL:
    d["_x"], d["_y"] = px(d["lon"], d["lat"])
OX, OY = px(ORG["lon"], ORG["lat"])

# ── 지역 bbox (딜 좌표에서, 여유 8도) ─────────────────────────
reg_deals = collections.defaultdict(list)
for d in SEL:
    reg_deals[d.get("region", "?")].append(d)

BBOX = {}
for k, v in reg_deals.items():
    lo = [d["lon"] for d in v]; la = [d["lat"] for d in v]
    BBOX[k] = (min(lo) - 8, min(la) - 8, max(lo) + 8, max(la) + 8)


def centroid(geom):
    pts = []

    def walk(c, depth):
        if depth == 0:
            pts.append(c)
        else:
            for x in c:
                walk(x, depth - 1)
    t = geom["type"]
    if t == "Polygon":
        walk(geom["coordinates"], 2)
    elif t == "MultiPolygon":
        walk(geom["coordinates"], 3)
    if not pts:
        return None
    return (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))


def region_of(c):
    """중심이 어느 지역 bbox에 드는가. 겹치면 중심이 더 가까운 쪽."""
    best, bestd = None, 1e9
    for k in PICK:
        b = BBOX.get(k)
        if not b:
            continue
        if b[0] <= c[0] <= b[2] and b[1] <= c[1] <= b[3]:
            cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
            dd = (c[0] - cx) ** 2 + (c[1] - cy) ** 2
            if dd < bestd:
                best, bestd = k, dd
    return best


def rings(geom):
    out = []
    t = geom["type"]
    if t == "Polygon":
        out = geom["coordinates"]
    elif t == "MultiPolygon":
        for poly in geom["coordinates"]:
            out.extend(poly)
    return out


def path_d(geom):
    """SVG path. 날짜변경선을 넘는 구간은 끊는다(far 중심이 142.9°E라 대서양에서 끊긴다)."""
    segs = []
    for ring in rings(geom):
        cur = []
        prev = None
        for lon, lat in ring:
            x, y = px(lon, lat)
            if prev is not None and abs(x - prev) > SW * 0.6:
                if len(cur) > 2:
                    segs.append(cur)
                cur = []
            cur.append("%.1f,%.1f" % (x, y))
            prev = x
        if len(cur) > 2:
            segs.append(cur)
    return " ".join("M" + " L".join(s) + "Z" for s in segs)


groups = collections.defaultdict(list)
n_assigned = 0
for f in W["features"]:
    c = centroid(f["geometry"])
    if not c:
        continue
    r = region_of(c)
    d = path_d(f["geometry"])
    if not d:
        continue
    groups[r or "_"].append(d)
    if r:
        n_assigned += 1

# ── 지역별 확대 아핀 계산 ─────────────────────────────────────
def affine(reg):
    v = [d for d in SEL if d.get("region") == reg]
    lons = sorted(d["lon"] for d in v)
    lats = [d["lat"] for d in v]
    if len(lons) > 1:
        gaps = [((lons[(i + 1) % len(lons)] - lons[i]) % 360, lons[(i + 1) % len(lons)])
                for i in range(len(lons))]
        g, b = max(gaps)
        arc = 360 - g
        lon_c = ((b + arc / 2.0 + 180) % 360) - 180
    else:
        arc, lon_c = 12.0, lons[0]
    lat_c = (min(lats) + max(lats)) / 2.0
    span_lat = max(6.0, max(lats) - min(lats))
    pad = 90
    k1 = min((SW - pad * 2) / 2.0 / max(1e-6, math.radians(arc / 2)),
             (SH - pad * 2) / 2.0 / max(1e-6, math.radians(span_lat / 2)))
    s = k1 / K0
    # x1 = s*(x0 - SW/2) + SW/2 + rad(lon0-lon_c)*k1   (경도 랩 처리)
    dlon = ((LON0 - lon_c + 180) % 360) - 180
    tx = SW / 2 + math.radians(dlon) * k1 - s * (SW / 2)
    ty = SH / 2 - math.radians(LAT0 - lat_c) * k1 - s * (SH / 2)
    return round(s, 4), round(tx, 1), round(ty, 1), int(k1)


AFF = {k: affine(k) for k in PICK if reg_deals.get(k)}

payload = []
for d in SEL:
    payload.append({"ko": d["ko"], "x": round(d["_x"], 1), "y": round(d["_y"], 1),
                    "r": d.get("region", "?"), "t": d.get("tier", "minor"),
                    "haul": d["haul"], "price": money(d["price"]),
                    "tier": tier(d) or ""})

EXTRA = """
.wrapG{max-width:1000px;margin:0 auto;padding:44px 26px 90px}
.try{background:var(--ink);color:#fff;border-radius:10px;padding:11px 16px;font-size:.86rem;
 font-weight:700;display:inline-flex;gap:9px;align-items:center;margin-bottom:14px}
.try b{color:#FFB9A5}
.stg{width:900px;height:560px;position:relative;background:var(--sea);
 border:1px solid #cfdad7;border-radius:14px;overflow:hidden}
svg.map{position:absolute;inset:0;width:900px;height:560px}
svg.map g.zoom{transition:transform .62s cubic-bezier(.22,.61,.36,1)}
svg.map path{fill:var(--land);stroke:#33534f22;stroke-width:.6;
 transition:fill .18s,stroke .18s}
svg.map g.reg{cursor:pointer}
svg.map g.reg:hover path,svg.map g.reg.on path{fill:#F6C3B2;stroke:#F2603F88;stroke-width:1}
.pinlayer{position:absolute;inset:0;pointer-events:none}
.pin{position:absolute;border-radius:99px;background:var(--accent);
 transition:left .62s cubic-bezier(.22,.61,.36,1),top .62s cubic-bezier(.22,.61,.36,1),
 width .3s,height .3s,margin .3s,opacity .3s}
.pin.maj{width:11px;height:11px;margin:-5.5px 0 0 -5.5px;box-shadow:0 0 0 3px rgba(242,96,63,.18)}
.pin.min{width:5px;height:5px;margin:-2.5px 0 0 -2.5px;opacity:.5}
.pin.org{background:var(--coast);width:13px;height:13px;margin:-6.5px 0 0 -6.5px;
 box-shadow:0 0 0 4px rgba(46,125,116,.2)}
.plab{position:absolute;transform:translate(-50%,-210%);font-size:.62rem;font-weight:800;
 background:#fff;border-radius:5px;padding:2px 7px;white-space:nowrap;box-shadow:0 2px 7px #0002;
 opacity:0;transition:opacity .3s .2s,left .62s cubic-bezier(.22,.61,.36,1),top .62s cubic-bezier(.22,.61,.36,1)}
.plab.on{opacity:1}
.bar{position:absolute;left:14px;top:14px;display:flex;gap:6px;z-index:9}
.bar2{position:absolute;left:14px;top:52px;display:flex;gap:6px;z-index:9}
.pill{background:#fff;border:1px solid var(--line);border-radius:99px;padding:6px 13px;
 font-size:.72rem;font-weight:800;color:var(--sub);box-shadow:0 2px 8px #0000000f;cursor:pointer;
 white-space:nowrap;transition:background .16s,color .16s,border-color .16s}
.pill.on{background:var(--ink);color:#fff;border-color:var(--ink)}
.pill.sub{border-color:#F2603F55;color:var(--accent);background:#FFF6F3}
.pill.sub.on{background:var(--accent);color:#fff;border-color:var(--accent)}
.pill .n{font-size:.62rem;opacity:.6;margin-left:5px;font-weight:700}
.hint{position:absolute;right:14px;bottom:14px;background:#fffffff2;border:1px solid var(--line);
 border-radius:9px;padding:7px 12px;font-size:.7rem;font-weight:700;color:var(--sub);z-index:9}
table{width:100%;border-collapse:collapse;font-size:.87rem;background:#fff;
 border:1px solid var(--line);border-radius:12px;overflow:hidden;max-width:760px}
th{text-align:left;font-size:.74rem;color:var(--sub);font-weight:800;padding:11px 12px;
 border-bottom:1px solid var(--line);background:var(--soft)}
td{padding:11px 12px;border-bottom:1px solid var(--line);vertical-align:top}
tr:last-child td{border-bottom:0}
td.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
"""

# ── SVG ────────────────────────────────────────────────────────
svg = '<svg class="map" viewBox="0 0 %d %d"><g class="zoom" id="zoom">' % (SW, SH)
svg += '<g class="rest">' + "".join('<path d="%s"/>' % d for d in groups.get("_", [])) + '</g>'
for k in PICK:
    if k in groups:
        svg += ('<g class="reg" id="g-%s" data-r="%s">' % (k, k)
                + "".join('<path d="%s"/>' % d for d in groups[k]) + '</g>')
svg += '</g></svg>'

BAR = ('<div class="bar"><span class="pill" id="back">가까운 곳</span>'
       '<span class="pill">조금 더 멀리</span>'
       '<span class="pill on" id="far">아주 멀리</span></div>')
BAR2 = '<div class="bar2">' + "".join(
    '<span class="pill sub" data-go="%s">%s<span class="n">%d</span></span>'
    % (k, KO[k], len([d for d in SEL if d.get("region") == k and d["haul"] == "long"]))
    for k in PICK if k in AFF) + '</div>'

JS = """
var AFF = __AFF__, PINS = __PINS__, SW = __SW__, SH = __SH__;
var zoom = document.getElementById('zoom'), layer = document.getElementById('pins');
var cur = null;

PINS.forEach(function (p, i) {
  var el = document.createElement('span');
  el.className = 'pin ' + (p.t === 'major' ? 'maj' : 'min');
  el.style.left = p.x + 'px'; el.style.top = p.y + 'px';
  el.dataset.i = i; layer.appendChild(el); p.el = el;
  var lb = document.createElement('span');
  lb.className = 'plab'; lb.textContent = p.ko;
  lb.style.left = p.x + 'px'; lb.style.top = p.y + 'px';
  layer.appendChild(lb); p.lb = lb;
});
var og = document.createElement('span');
og.className = 'pin org';
og.style.left = __OX__ + 'px'; og.style.top = __OY__ + 'px';
layer.appendChild(og);

function apply(r) {
  cur = r;
  var a = r ? AFF[r] : [1, 0, 0, 0];
  zoom.style.transform = 'translate(' + a[1] + 'px,' + a[2] + 'px) scale(' + a[0] + ')';
  og.style.opacity = r ? 0 : 1;
  PINS.forEach(function (p) {
    var x = a[0] * p.x + a[1], y = a[0] * p.y + a[2];
    p.el.style.left = x + 'px'; p.el.style.top = y + 'px';
    p.lb.style.left = x + 'px'; p.lb.style.top = y + 'px';
    var inreg = !r || p.r === r;
    p.el.style.opacity = inreg ? (p.t === 'major' ? 1 : .5) : .12;
    p.lb.classList.toggle('on', !!r && p.r === r);
  });
  document.querySelectorAll('.reg').forEach(function (g) {
    g.classList.toggle('on', g.dataset.r === r);
  });
  document.querySelectorAll('[data-go]').forEach(function (b) {
    b.classList.toggle('on', b.dataset.go === r);
  });
  document.getElementById('far').classList.toggle('on', !r);
}

document.querySelectorAll('.reg').forEach(function (g) {
  g.addEventListener('click', function () { apply(g.dataset.r === cur ? null : g.dataset.r); });
});
document.querySelectorAll('[data-go]').forEach(function (b) {
  b.addEventListener('click', function () { apply(b.dataset.go === cur ? null : b.dataset.go); });
});
document.getElementById('far').addEventListener('click', function () { apply(null); });
apply(null);
"""

js = (JS.replace("__AFF__", json.dumps({k: list(v[:3]) for k, v in AFF.items()}))
        .replace("__PINS__", json.dumps(payload, ensure_ascii=False))
        .replace("__SW__", str(SW)).replace("__SH__", str(SH))
        .replace("__OX__", "%.1f" % OX).replace("__OY__", "%.1f" % OY))

trs = "".join(
    '<tr><td class="k">%s</td><td class="num">%d조각</td><td class="num">%d건</td>'
    '<td class="num">%.1f배</td><td class="num">%d</td></tr>'
    % (KO[k], len(groups.get(k, [])),
       len([d for d in SEL if d.get("region") == k and d["haul"] == "long"]),
       AFF[k][0], AFF[k][3])
    for k in PICK if k in AFF)

html = ("<!doctype html><html lang=ko><head><meta charset=utf-8>"
        "<meta name=viewport content='width=device-width,initial-scale=1'>"
        "<title>갈래말래 — 대륙 호버</title><style>" + CSS + EXTRA +
        "</style></head><body><div class=wrapG>"
        "<h1>대륙 호버 &mdash; <em>땅을 고른다</em></h1>"
        "<p class=lede>게임에서 영토 고르듯, <b>마우스를 올리면 그 대륙이 밝아지고 누르면 들어간다.</b> "
        "실제 <code>world.geojson</code> 182조각과 서울 출발 " + str(len(SEL)) + "건으로 그렸다.</p>"
        "<div class=try>&#128070; <b>지도의 유럽·미주·오세아니아에 마우스를 올려보세요</b> "
        "&mdash; 누르면 들어가고, <code>아주 멀리</code>를 누르면 돌아옵니다.</div>"
        '<div class="stg">' + svg +
        '<div class="pinlayer" id="pins"></div>' + BAR + BAR2 +
        '<div class="hint">호버 → 대륙이 밝아짐 · 클릭 → 확대</div></div>'
        "<h2><span class=n>01</span>어떻게 됐나</h2>"
        "<table><tr><th>대륙</th><th style='text-align:right'>육지 조각</th>"
        "<th style='text-align:right'>장거리 딜</th><th style='text-align:right'>확대</th>"
        "<th style='text-align:right'>배율</th></tr>" + trs + "</table>"
        "<p class=note>육지 조각 <b>" + str(n_assigned) + "개</b>가 세 대륙에 배정됐다"
        "(전체 182개 중). 나머지는 회색으로 남는다.</p>"
        "<h2><span class=n>02</span>속성 없이 어떻게 했나</h2>"
        "<div class=callout><b><code>world.geojson</code>에 속성이 하나도 없다</b> &mdash; "
        "182개 feature가 전부 <code>{}</code>다. <b>어느 조각이 프랑스인지 알 수 없다.</b><br>"
        "→ 각 조각의 <b>중심 좌표</b>를 계산해서 <b>딜 좌표로 만든 지역 상자</b>에 넣었다. "
        "<b>속성이 없어도 된다.</b></div>"
        "<ul class=k>"
        "<li><b>딜이 없는 나라도 같이 밝아진다.</b> 유럽을 올리면 벨기에·폴란드도 밝아진다 &mdash; "
        "<b>그게 &lsquo;대륙 모양&rsquo;이라 오히려 요청에 가깝다.</b> "
        "지금은 <b>어디로 갈지</b>를 고르는 단계고, 딜은 들어간 다음에 본다.</li>"
        "<li><b>확대는 CSS <code>transform</code> 한 번</b>이다. 등거리원통도법이 경위도에 선형이라 "
        "center·scale 변경이 <b>평면 아핀변환</b>이 된다 &mdash; "
        "프론트가 CH1 T5에서 쓴 그 원리 그대로다(<b>path를 다시 안 만든다</b>).</li>"
        "<li><b>핀은 변환 그룹 밖</b>에 있다. 안에 넣으면 확대할 때 <b>핀도 같이 커진다.</b> "
        "같은 아핀을 좌표에만 적용해 <b>크기는 그대로</b> 둔다.</li>"
        "<li><b>들어가면 그 대륙 딜만 진하다.</b> 나머지는 흐려진다 &mdash; "
        "숨기지 않는다(<b>F15</b>). 라벨도 그때만 뜬다.</li>"
        "</ul>"
        "<h2><span class=n>03</span>정할 것</h2>"
        "<table><tr><th style='width:200px'>안건</th><th>메모</th></tr>"
        "<tr><td class=k>딜이 없는 대륙</td><td>지금은 <b>셋 다 딜이 있어</b> 문제가 없다. "
        "없는 날엔 <b>그 대륙을 아예 안 밝히는</b> 게 맞다 &mdash; 눌러도 빈 화면이면 배신이다.</td></tr>"
        "<tr><td class=k>&lsquo;그 외&rsquo; 4건</td><td>콜롬보·두바이·호놀룰루·괌은 <b>서로 멀어 한 화면에 안 담긴다.</b> "
        "칩을 <b>안 두는</b> 쪽으로 그렸다.</td></tr>"
        "<tr><td class=k>가까운 대륙</td><td>동남아·중국·일본은 <b>단계 버튼이 이미 해결</b>한다. "
        "<code>아주 멀리</code>에서만 대륙을 연다.</td></tr>"
        "<tr><td class=k>모바일</td><td>호버가 없다. <b>탭 = 선택</b>이 되므로 "
        "칩(아래 줄)이 주 조작이 된다.</td></tr>"
        "</table>"
        "<p class=note>&#9888; <b>이 세션엔 브라우저가 없어 실제 렌더를 못 봤다.</b> "
        "대륙 경계가 자연스러운지, 호버 색이 과한지는 <b>눈으로 봐야</b> 안다.</p>"
        "<p class=foot>생성 <b>design/build_region.py</b> &middot; "
        "데이터 <b>world.geojson</b>(182조각) · <b>deals.json</b>(서울 " + str(len(SEL)) + "건) &middot; "
        "대륙 진입 <b>far.html</b> &middot; 핀 밀도 <b>pins.html</b></p>"
        "</div><script>" + js + "</script></body></html>")

io.open(os.path.join(BASE, "region.html"), "w", encoding="utf-8").write(html)
print("region.html  %.0f KB" % (len(html) / 1024.0))
print("  육지 조각 %d개 중 %d개 배정" % (len(W["features"]), n_assigned))
for k in PICK:
    if k in AFF:
        print("  %-4s %2d조각 · 확대 %.1f배 · 배율 %d"
              % (k, len(groups.get(k, [])), AFF[k][0], AFF[k][3]))
