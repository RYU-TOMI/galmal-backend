# -*- coding: utf-8 -*-
"""상세 열림 동작 — "스르륵" (E1 + 이동).

실제로 눌러볼 수 있는 목업이다. 카드를 누르면 지도가 그 핀으로 미끄러지고
카드가 핀에서 피어난다. 실제 deals.json 좌표를 등장방형으로 투영해 그린다.
소유: 기획 세션. 산출물 design/open.html
"""
import json, io, os, math

BASE = os.path.dirname(os.path.abspath(__file__))
D = json.load(io.open(os.path.join(BASE, "..", "docs", "data", "deals.json"), encoding="utf-8"))

TOP = ["해변", "도시", "미식", "자연", "문화", "온천"]
SUB = {"리조트", "스노클링", "서핑", "섬", "야경", "쇼핑", "마천루", "골목",
       "야시장", "길거리음식", "화산", "트레킹", "사막", "폭포", "사원", "유적", "고성", "미술관"}
TIERS = [(35, "t3"), (25, "t2"), (15, "t1")]


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
SEOUL = D["origins"]["SEL"]

# ── 무대 좌표계 ────────────────────────────────────────────────
# 목업 지도 캔버스(도 단위 → px). 실제는 d3-geo가 하지만 여기선 선형 근사로 충분하다.
LON0, LAT0 = 118.0, 22.0        # 캔버스 중심
KX, KY = 7.2, 8.6               # 도당 px
CANVAS_W, CANVAS_H = 1500, 900  # 캔버스 전체(무대보다 크다 — 이만큼 팬할 수 있다)
STAGE_W, STAGE_H = 620, 420     # 보이는 무대


def proj(lon, lat):
    return (CANVAS_W / 2.0 + (lon - LON0) * KX,
            CANVAS_H / 2.0 - (lat - LAT0) * KY)


# 무대 안에 들어오는 딜만 목업에 쓴다(캔버스 밖은 의미 없음)
SHOW = []
for d in deals:
    x, y = proj(d["lon"], d["lat"])
    if 60 < x < CANVAS_W - 60 and 50 < y < CANVAS_H - 50:
        SHOW.append(dict(d, _x=round(x, 1), _y=round(y, 1)))
SHOW = SHOW[:14]
OX, OY = proj(SEOUL["lon"], SEOUL["lat"])

payload = []
for d in SHOW:
    payload.append({
        "d": d["d"], "ko": d["ko"], "price": money(d["price"]),
        "raw": d["price"], "dep": d["dep"], "nights": d.get("nights", ""),
        "disc": d.get("discount", 0), "tier": tier(d) or "",
        "direct": bool(direct(d)), "tags": card_tags(d["tags"]),
        "median": money(d.get("median") or int(d["price"] * 1.25)),
        "ratio": int(min(1.0, d["price"] / float(d.get("median") or d["price"] * 1.25)) * 100),
        "x": d["_x"], "y": d["_y"],
    })

CSS = """
:root{--ink:#17201F;--sub:#6C7B78;--line:#E3EAE8;--soft:#F2F6F5;
 --accent:#F2603F;--coast:#2E7D74;--sea:#EAF1F0;--land:#DCE6E3}
*{box-sizing:border-box}
body{margin:0;font:14px/1.6 -apple-system,"Segoe UI",Roboto,"Malgun Gothic",sans-serif;
 color:var(--ink);background:var(--sea)}
.wrap{max-width:1180px;margin:0 auto;padding:44px 30px 90px}
h1{font-size:1.9rem;letter-spacing:-.03em;margin:0 0 6px}
h1 em{font-style:normal;color:var(--accent)}
.lede{color:var(--sub);margin:0 0 30px;max-width:820px;line-height:1.75}
h2{font-size:1.12rem;margin:52px 0 8px;display:flex;align-items:center;gap:10px}
h2 .n{font-size:.68rem;background:var(--ink);color:#fff;border-radius:5px;padding:2px 7px;font-weight:800}
.note{color:var(--sub);font-size:.88rem;line-height:1.75;margin:0 0 18px;max-width:880px}
.try{background:var(--ink);color:#fff;border-radius:10px;padding:11px 16px;font-size:.86rem;
 font-weight:700;display:inline-flex;gap:9px;align-items:center;margin-bottom:14px}
.try b{color:#FFB9A5}
/* ── 데모 셸 ── */
.shell{display:flex;width:1000px;height:420px;border:1px solid var(--line);
 border-radius:16px;overflow:hidden;background:#fff;box-shadow:0 10px 30px #0000000d}
.stage{width:620px;flex:none;position:relative;overflow:hidden;background:var(--sea)}
.canvas{position:absolute;width:1500px;height:900px;left:0;top:0;
 transition:transform .62s cubic-bezier(.22,.61,.36,1)}
.land{position:absolute;border-radius:46% 54% 40% 60%/50% 44% 56% 50%;background:var(--land)}
.pin{position:absolute;width:10px;height:10px;margin:-5px 0 0 -5px;border-radius:99px;
 background:var(--accent);box-shadow:0 0 0 3px rgba(242,96,63,.2);cursor:pointer;
 transition:width .3s,height .3s,margin .3s,box-shadow .3s;z-index:2}
.pin.on{width:18px;height:18px;margin:-9px 0 0 -9px;box-shadow:0 0 0 7px rgba(242,96,63,.28);z-index:4}
.pin.orig{background:var(--coast);box-shadow:0 0 0 3px rgba(46,125,116,.22)}
.plab{position:absolute;transform:translate(-50%,-190%);font-size:.6rem;font-weight:800;
 background:#fff;border-radius:5px;padding:2px 7px;white-space:nowrap;
 box-shadow:0 2px 7px #0002;opacity:0;transition:opacity .3s .18s;pointer-events:none;z-index:5}
.plab.on{opacity:1}
svg.arcs{position:absolute;inset:0;width:1500px;height:900px;pointer-events:none;z-index:1}
svg.arcs path{fill:none;stroke:var(--accent);stroke-width:1.6;opacity:0;
 stroke-dasharray:var(--len);stroke-dashoffset:var(--len);transition:opacity .2s}
svg.arcs path.on{opacity:.75;animation:draw .5s cubic-bezier(.22,.61,.36,1) forwards}
@keyframes draw{to{stroke-dashoffset:0}}
/* 핀에서 피어나는 카드 */
.pop{position:absolute;width:212px;z-index:6;opacity:0;pointer-events:none;
 transform:translate(-50%,-100%) scale(.86);transform-origin:50% 106%;
 transition:opacity .2s,transform .34s cubic-bezier(.2,.9,.3,1.2)}
.pop.on{opacity:1;pointer-events:auto;transform:translate(-50%,-100%) scale(1)}
.pop:after{content:"";position:absolute;left:50%;bottom:-7px;margin-left:-7px;
 border:7px solid transparent;border-top-color:#fff}
/* ── 패널 ── */
.panel{flex:1;background:var(--sea);border-left:1px solid var(--line);padding:0 10px;
 overflow-y:auto;position:relative}
.sortbar{position:sticky;top:0;background:var(--sea);height:42px;display:flex;
 align-items:center;gap:5px;font-size:.58rem;z-index:3}
.spill{background:#fff;border:1px solid var(--line);border-radius:99px;padding:3px 9px;font-weight:800;color:var(--sub)}
.spill.on{background:var(--ink);color:#fff;border-color:var(--ink)}
.feed{display:flex;flex-direction:column;gap:7px;padding-bottom:12px}
.fcard{display:flex;gap:9px;background:#fff;border:1.5px solid var(--line);border-radius:11px;
 padding:8px;cursor:pointer;transition:border-color .16s,box-shadow .16s,transform .16s}
.fcard:hover{border-color:#c9d6d3;transform:translateY(-1px)}
.fcard.on{border-color:var(--accent);box-shadow:0 5px 16px rgba(242,96,63,.2)}
.thumb{flex:none;width:52px;height:52px;border-radius:8px;
 background:linear-gradient(140deg,#cfe0dc,#e9efed)}
.fbody{flex:1;min-width:0}
.frow{display:flex;justify-content:space-between;align-items:center;gap:5px}
.fcity{font-size:.82rem;font-weight:900;letter-spacing:-.02em;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.prow{display:flex;justify-content:space-between;align-items:center;gap:6px;margin-top:2px}
.price{font-weight:900;font-size:.95rem;letter-spacing:-.03em;font-variant-numeric:tabular-nums}
.price small{font-size:.62em;font-weight:700;color:var(--sub);margin-left:1px}
.dmain{font-size:.6rem;font-weight:800;margin-top:4px;font-variant-numeric:tabular-nums}
.dsub{font-size:.55rem;font-weight:700;color:var(--sub);font-variant-numeric:tabular-nums}
.wk{color:var(--sub);font-weight:700}
.bdg{font-size:.5rem;font-weight:800;border-radius:99px;padding:1px 6px;flex:none;
 background:var(--coast);color:#fff;white-space:nowrap}
.stamp{flex:none;font-weight:900;white-space:nowrap;border-radius:3px}
.stamp.t1{transform:rotate(-7deg);border:1.2px solid var(--accent);color:var(--accent);font-size:.46rem;padding:1px 4px;background:#fff}
.stamp.t2{transform:rotate(-8deg);background:var(--accent);color:#fff;font-size:.5rem;padding:1px 5px}
.stamp.t3{transform:rotate(-9deg);background:linear-gradient(135deg,#F2603F,#FF8A63 42%,#C6472A);
 color:#fff;font-size:.52rem;padding:1px 6px;box-shadow:0 0 0 1.5px #fff,0 0 0 3px rgba(242,96,63,.2)}
/* 상세 내용 */
.det{background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 12px 32px rgba(20,40,36,.26)}
.det .ph{height:88px;position:relative;background:linear-gradient(140deg,#bcd3ce,#dde8e5)}
.phtags{position:absolute;left:6px;right:6px;bottom:6px;display:flex;gap:3px;flex-wrap:wrap}
.phtag{font-size:.5rem;font-weight:800;color:#fff;background:rgba(6,20,18,.5);
 border-radius:4px;padding:1px 6px;white-space:nowrap}
.cityover{position:absolute;left:8px;bottom:22px;color:#fff;font-weight:900;font-size:.92rem;
 text-shadow:0 1px 6px #0009;letter-spacing:-.02em}
.closex{position:absolute;right:6px;top:6px;width:19px;height:19px;border-radius:99px;
 background:rgba(6,20,18,.45);color:#fff;font-size:.62rem;font-weight:900;cursor:pointer;
 display:flex;align-items:center;justify-content:center}
.db{padding:9px}
.dsec{font-size:.54rem;font-weight:800;color:var(--sub);margin:9px 0 5px;padding-top:8px;
 border-top:1px dashed var(--line)}
.cmp{display:flex;align-items:center;gap:6px;font-size:.56rem;margin:3px 0}
.cmp .bar{flex:1;height:6px;border-radius:99px;background:var(--soft);overflow:hidden}
.cmp .bar i{display:block;height:100%;border-radius:99px;background:var(--accent)}
.cmp .bar.mut i{background:#c3cfcc}
.cmp b{font-variant-numeric:tabular-nums;white-space:nowrap;font-size:.58rem}
.go{margin-top:8px;background:var(--accent);color:#fff;text-align:center;font-weight:800;
 font-size:.64rem;border-radius:8px;padding:7px 0}
.ad{font-size:.47rem;color:var(--sub);line-height:1.5;margin-top:6px;text-align:center}
.hashbar{margin-top:10px;font-family:ui-monospace,Consolas,monospace;font-size:.76rem;
 background:var(--ink);color:#8FE3D0;border-radius:8px;padding:8px 12px;display:inline-block}
.hashbar b{color:#fff}
table{width:100%;border-collapse:collapse;font-size:.86rem;background:#fff;
 border:1px solid var(--line);border-radius:12px;overflow:hidden}
th{text-align:left;font-weight:700;font-size:.74rem;color:var(--sub);padding:11px 12px;
 border-bottom:1px solid var(--line);background:var(--soft)}
td{padding:11px 12px;border-bottom:1px solid var(--line);vertical-align:top}
tr:last-child td{border-bottom:0}
td.num{font-variant-numeric:tabular-nums;white-space:nowrap}
.callout{background:#fff;border:1px solid var(--line);border-left:3px solid var(--accent);
 border-radius:10px;padding:16px 18px;margin:18px 0;font-size:.92rem;line-height:1.8;max-width:900px}
.callout b{color:var(--accent)}
ul.k{margin:12px 0 0;padding-left:19px;color:var(--sub);font-size:.89rem;max-width:900px}
ul.k li{margin:8px 0}ul.k b{color:var(--ink)}
code{font-family:ui-monospace,Consolas,monospace;font-size:.85em;background:var(--soft);padding:1px 5px;border-radius:4px}
.foot{margin-top:60px;padding-top:18px;border-top:1px solid var(--line);font-size:.8rem;color:var(--sub)}
@media (prefers-reduced-motion:reduce){
  .canvas,.pop,.pin,.plab{transition:none!important}
  svg.arcs path.on{animation:none;stroke-dashoffset:0}
}
"""

JS = """
var DEALS = __PAYLOAD__;
var OX = __OX__, OY = __OY__;
var SW = __SW__, SH = __SH__, CW = __CW__, CH = __CH__;
var canvas = document.getElementById('canvas'),
    pop = document.getElementById('pop'),
    arcs = document.getElementById('arcs'),
    feed = document.getElementById('feed'),
    stage = document.getElementById('stage'),
    hash = document.getElementById('hash');
var open_ = null;

function clamp(v, lo, hi){ return Math.max(lo, Math.min(hi, v)); }

/* 카드가 핀 위로 피어나므로, 핀이 무대 위쪽 40%쯤에 오도록 민다.
   캔버스가 무대보다 크므로 가장자리에서는 클램프한다. */
function panTo(d){
  var tx = clamp(SW*0.46 - d.x, SW - CW, 0);
  var ty = clamp(SH*0.62 - d.y, SH - CH, 0);
  canvas.style.transform = 'translate(' + tx + 'px,' + ty + 'px)';
  return {tx: tx, ty: ty};
}

function arcPath(d){
  var mx = (OX + d.x)/2, my = (OY + d.y)/2 - Math.abs(d.x - OX)*0.18 - 20;
  return 'M' + OX + ',' + OY + ' Q' + mx + ',' + my + ' ' + d.x + ',' + d.y;
}

function detailHTML(d){
  var stamp = d.tier ? '<span class="stamp ' + d.tier + '">' + d.disc + '%\\u2193</span>' : '';
  var bdg = d.direct ? '<span class="bdg">\\u2708 \\uc9c1\\ud56d</span>' : '';
  var tags = d.tags.map(function(t){ return '<span class="phtag">' + t + '</span>'; }).join('');
  return '<div class="det"><div class="ph"><span class="closex" id="cx">\\u00d7</span>' +
    '<div class="phtags">' + tags + '</div>' +
    '<span class="cityover">' + d.ko + '</span></div><div class="db">' +
    '<div class="prow" style="margin-top:0"><span class="price" style="font-size:1.04rem">' +
    d.price + '<small>\\uc6d0</small></span>' + stamp + '</div>' +
    '<div class="prow" style="margin-top:3px"><span class="dmain" style="margin-top:0">' +
    d.dep + ' <span class="wk">\\u00b7 ' + d.nights + '</span></span>' + bdg + '</div>' +
    '<div class="dsec">\\ud3c9\\uc18c \\uc2dc\\uc138\\uc640 \\ube44\\uad50</div>' +
    '<div class="cmp"><span style="width:38px;color:var(--sub)">\\ud3c9\\uc18c</span>' +
    '<span class="bar mut"><i style="width:100%"></i></span><b>' + d.median + '\\uc6d0</b></div>' +
    '<div class="cmp"><span style="width:38px;font-weight:800">\\uc9c0\\uae08</span>' +
    '<span class="bar"><i style="width:' + d.ratio + '%"></i></span><b>' + d.price + '\\uc6d0</b></div>' +
    '<div class="go">\\uac08\\ub798 \\u2192 \\uc608\\uc57d\\ucc98\\ub85c</div>' +
    '<div class="ad">\\uc704 \\uac00\\uaca9\\uc740 \\ubc1c\\uacac\\uac00(\\uc2a4\\uce94 \\uc2dc\\uc810) \\u00b7 ' +
    '\\uc2e4\\uc2dc\\uac04 \\ucd5c\\uc800\\uac00\\ub294 \\uac01 \\uc0ac\\uc774\\ud2b8\\uc5d0\\uc11c \\ud655\\uc778\\ud558\\uc138\\uc694</div>' +
    '</div></div>';
}

function close_(){
  if (!open_) return;
  pop.classList.remove('on');
  document.querySelectorAll('.pin.on,.plab.on,.fcard.on,#arcs path.on')
    .forEach(function(el){ el.classList.remove('on'); });
  open_ = null;
  hash.innerHTML = '<b>#SEL</b>';
}

function openDeal(code, fromPin){
  var d = DEALS.filter(function(x){ return x.d === code; })[0];
  if (!d) return;
  if (open_ === code) { close_(); return; }
  close_();
  open_ = code;

  panTo(d);
  document.getElementById('pin-' + code).classList.add('on');
  document.getElementById('lab-' + code).classList.add('on');
  document.getElementById('arc-' + code).classList.add('on');
  var card = document.getElementById('card-' + code);
  card.classList.add('on');
  if (fromPin) {
    /* scrollIntoView는 문서까지 굴려 페이지가 튄다. 패널만 굴린다. */
    var panel = card.parentNode.parentNode;
    var top = card.offsetTop - (panel.clientHeight - card.offsetHeight) / 2;
    var smooth = !window.matchMedia('(prefers-reduced-motion:reduce)').matches;
    if (panel.scrollTo) panel.scrollTo({top: top, behavior: smooth ? 'smooth' : 'auto'});
    else panel.scrollTop = top;
  }

  pop.style.left = d.x + 'px';
  pop.style.top  = (d.y - 14) + 'px';
  pop.innerHTML = detailHTML(d);
  /* 지도가 미끄러지는 동안 기다렸다가 카드를 피운다 — 시선이 따라온 뒤에 열린다 */
  var wait = window.matchMedia('(prefers-reduced-motion:reduce)').matches ? 0 : 300;
  setTimeout(function(){ pop.classList.add('on'); }, wait);
  hash.innerHTML = '<b>#SEL-' + code + '</b>';

  setTimeout(function(){
    var cx = document.getElementById('cx');
    if (cx) cx.addEventListener('click', function(e){ e.stopPropagation(); close_(); });
  }, wait + 20);
}

DEALS.forEach(function(d){
  document.getElementById('pin-' + d.d)
    .addEventListener('click', function(e){ e.stopPropagation(); openDeal(d.d, true); });
  document.getElementById('card-' + d.d)
    .addEventListener('click', function(){ openDeal(d.d, false); });
});
/* 상세 안을 누르면 stage로 버블링돼 곧바로 닫히던 버그 — 여기서 막는다 */
pop.addEventListener('click', function(e){ e.stopPropagation(); });
stage.addEventListener('click', function(){ close_(); });

/* 항로 길이를 재서 그려지는 애니메이션에 쓴다 */
document.querySelectorAll('#arcs path').forEach(function(p){
  var L = p.getTotalLength();
  p.style.setProperty('--len', L);
});
"""


def small_card(d):
    t = d["tier"]
    stamp = ('<span class="stamp %s">%d%%&darr;</span>' % (t, d["disc"])) if t else ""
    bdg = '<span class="bdg">&#9992;</span>' if d["direct"] else ""
    return ('<div class="fcard" id="card-%s">'
            '<div class="thumb"></div><div class="fbody">'
            '<div class="frow"><span class="fcity">%s</span>%s</div>'
            '<div class="prow"><span class="price">%s<small>원</small></span>%s</div>'
            '<div class="dmain">%s <span class="dsub wk">&middot; %s</span></div>'
            '</div></div>' % (d["d"], d["ko"], stamp, d["price"], bdg, d["dep"], d["nights"]))


pins = '<span class="pin orig" style="left:%.1fpx;top:%.1fpx" title="서울"></span>' % (OX, OY)
labs = ""
paths = ""
for d in payload:
    pins += '<span class="pin" id="pin-%s" style="left:%.1fpx;top:%.1fpx"></span>' % (d["d"], d["x"], d["y"])
    labs += ('<span class="plab" id="lab-%s" style="left:%.1fpx;top:%.1fpx">%s</span>'
             % (d["d"], d["x"], d["y"], d["ko"]))
    mx = (OX + d["x"]) / 2.0
    my = (OY + d["y"]) / 2.0 - abs(d["x"] - OX) * 0.18 - 20
    paths += ('<path id="arc-%s" d="M%.1f,%.1f Q%.1f,%.1f %.1f,%.1f"/>'
              % (d["d"], OX, OY, mx, my, d["x"], d["y"]))

lands = ""
for lx, ly, lw, lh in [(230, 180, 420, 300), (620, 130, 330, 250), (400, 470, 300, 220),
                       (830, 380, 260, 200), (140, 430, 200, 170), (980, 180, 300, 240)]:
    lands += ('<div class="land" style="left:%dpx;top:%dpx;width:%dpx;height:%dpx"></div>'
              % (lx, ly, lw, lh))

js = (JS.replace("__PAYLOAD__", json.dumps(payload, ensure_ascii=False))
        .replace("__OX__", "%.1f" % OX).replace("__OY__", "%.1f" % OY)
        .replace("__SW__", str(STAGE_W)).replace("__SH__", str(STAGE_H))
        .replace("__CW__", str(CANVAS_W)).replace("__CH__", str(CANVAS_H)))

html = (
    "<!doctype html><html lang=ko><head><meta charset=utf-8>"
    "<meta name=viewport content='width=device-width,initial-scale=1'>"
    "<title>갈래말래 — 상세 열림</title><style>" + CSS + "</style></head><body><div class=wrap>"
    "<h1>상세 열림 &mdash; <em>스르륵</em></h1>"
    "<p class=lede>지도 위에 띄우되(<b>E1</b>), <b>지도가 그 자리로 미끄러진 뒤</b> 카드가 핀에서 피어난다. "
    "시선이 튀는 게 아니라 <b>시선을 데려간다.</b> 서울 출발 실제 딜 좌표로 그렸다.</p>"

    "<div class=try>&#128070; <b>눌러보세요</b> &mdash; 오른쪽 카드나 지도의 점을 누르면 움직입니다. "
    "빈 곳을 누르면 닫힙니다.</div>"

    "<div class=shell>"
    "<div class=stage id=stage><div class=canvas id=canvas>" + lands +
    "<svg class=arcs id=arcs viewBox='0 0 1500 900'>" + paths + "</svg>" +
    pins + labs +
    "<div class=pop id=pop></div></div></div>"
    "<div class=panel><div class=sortbar><span class='spill on'>가성비순</span>"
    "<span class=spill>임박순</span><span class=spill>할인율순</span></div>"
    "<div class=feed id=feed>" + "".join(small_card(d) for d in payload) + "</div></div>"
    "</div>"
    "<div class=hashbar id=hash><b>#SEL</b></div>"

    "<h2><span class=n>01</span>왜 E1로 돌아왔나</h2>"
    "<div class=callout>내가 E1을 반대한 이유는 <b>&ldquo;시선이 튄다&rdquo;</b>였다. "
    "그런데 <b>지도가 스르륵 움직이면 시선이 따라간다.</b><br>"
    "튀는 게 문제였는데 움직임이 그걸 없앤다. 오히려 "
    "<b>&lsquo;네가 고른 곳은 여기다&rsquo;를 말해 주는 장치</b>가 된다 &mdash; "
    "지도가 본체인 서비스에서 이건 큰 이득이다.</div>"
    "<ul class=k>"
    "<li><b>B14와의 결합도 이 방식이 푼다.</b> 핀이 화면 밖이면 열 자리가 없다는 게 E1의 약점이었는데, "
    "<b>지도가 그 핀으로 이동하니</b> 항상 자리가 생긴다. 약점이 기능이 됐다.</li>"
    "<li><b>배율은 안 건드린다.</b> 거리 단계(가까운 곳/조금 더 멀리/아주 멀리)가 뷰를 정하는 모델이라, "
    "여기서 확대까지 하면 단계 모델이 깨진다. <b>이동만</b> 한다.</li>"
    "<li><b>핀을 무대 중앙이 아니라 아래쪽 62%에 놓는다.</b> 카드가 핀 <b>위로</b> 피어나기 때문이다. "
    "가운데에 두면 카드가 무대 밖으로 넘친다.</li>"
    "</ul>"

    "<h2><span class=n>02</span>타이밍</h2>"
    "<table><tr><th>순서</th><th>무엇이</th><th class=num>시간</th><th>곡선</th></tr>"
    "<tr><td>1</td><td>지도가 그 핀으로 미끄러진다</td><td class=num>620ms</td>"
    "<td><code>cubic-bezier(.22,.61,.36,1)</code> &mdash; 빠르게 출발해 부드럽게 선다</td></tr>"
    "<tr><td>1</td><td>핀이 커지고 이름표가 뜬다</td><td class=num>300ms</td><td>이동과 <b>동시에</b></td></tr>"
    "<tr><td>1</td><td>항로가 서울에서 그려진다</td><td class=num>500ms</td>"
    "<td><code>stroke-dashoffset</code> &mdash; 출발지와 이어져 있음을 보인다</td></tr>"
    "<tr><td>2</td><td>카드가 핀에서 피어난다</td><td class=num>+300ms 뒤 340ms</td>"
    "<td><code>cubic-bezier(.2,.9,.3,1.2)</code> &mdash; 살짝 튀어 &lsquo;열렸다&rsquo;는 감각</td></tr></table>"
    "<p class=note><b>왜 300ms를 기다리나</b> &mdash; 지도가 아직 움직이는 중에 카드가 뜨면 "
    "카드가 미끄러지는 것처럼 보인다. <b>시선이 목적지에 도착한 뒤</b> 열어야 &lsquo;여기다&rsquo;가 된다. "
    "전체 체감은 <b>0.9초</b>다.</p>"
    "<p class=note>&#9888; <b><code>prefers-reduced-motion</code>이면 전부 0ms</b>다. "
    "이동도 등장도 즉시. 어지럼증을 유발하는 큰 화면 이동이라 <b>선택이 아니라 필수</b>다. "
    "이 목업도 그렇게 만들었다.</p>"

    "<h2><span class=n>03</span>열고 닫기</h2>"
    "<table><tr><th>동작</th><th>결과</th></tr>"
    "<tr><td>카드를 누른다</td><td>지도가 이동 &rarr; 핀 확대 + 이름표 + 항로 &rarr; 카드가 핀에서 피어남 "
    "&middot; <code>#SEL-{목적지}</code></td></tr>"
    "<tr><td><b>핀을 누른다</b></td><td>같은 동작 + <b>패널이 그 카드로 스크롤</b>해 강조한다 &mdash; "
    "양방향이 대칭이다</td></tr>"
    "<tr><td>다른 카드/핀을 누른다</td><td>먼저 것이 닫히고 지도가 새 곳으로 미끄러진다 <b>(동시에 하나만)</b></td></tr>"
    "<tr><td>&times; · 같은 것 다시 · 빈 지도</td><td>카드만 닫힌다. <b>지도는 그 자리에 둔다</b> &mdash; "
    "되돌리면 방금 온 길이 무의미해지고 멀미가 난다</td></tr>"
    "<tr><td>브라우저 뒤로가기</td><td>사이트를 안 떠나고 상세만 닫힌다 &middot; <code>#SEL</code></td></tr>"
    "<tr><td>정렬·필터를 바꾼다</td><td>닫는다. <b>지도는 그대로</b></td></tr>"
    "<tr><td>거리 단계를 바꾼다</td><td>닫는다. 뷰가 통째로 바뀌므로 이동 상태도 초기화한다</td></tr>"
    "<tr><td>딥링크로 들어온다</td><td>단계를 딜의 <code>haul</code>에 맞추고 <b>이동 없이</b> 그 위치에서 시작한다 "
    "&mdash; 첫 화면부터 움직이면 어지럽다</td></tr>"
    "<tr><td>그 딜이 오늘 없다</td><td>출발지만 적용 + 안내(F5). 다른 허브에 같은 목적지가 있으면 제안</td></tr>"
    "<tr><td><b>모바일</b>(&le;860px)</td><td>이동 없이 <b>하단 시트</b>. 화면이 좁아 카드가 지도를 다 덮는다 "
    "&mdash; 현행 분기를 유지한다</td></tr></table>"

    "<h2><span class=n>04</span>남은 것</h2>"
    "<ul class=k>"
    "<li><b>이 목업은 선형 근사다.</b> 실제 지도는 <code>d3.geoEquirectangular</code>이므로 "
    "이동은 <code>translate</code>가 아니라 <b><code>rotate</code>/<code>center</code> 보간</b>이 된다. "
    "느낌은 같지만 구현은 프론트가 정한다.</li>"
    "<li><b>이동량이 클 때</b>(예: 다낭 &rarr; 뉴욕) 620ms가 짧을 수 있다. "
    "거리에 따라 <b>420~760ms</b>로 조절하는 걸 제안한다 &mdash; 짧은 이동이 느리면 굼떠 보인다.</li>"
    "<li><b>이동 중 다른 카드를 누르면</b> 진행 중인 이동을 <b>가로채</b> 새 목적지로 간다. "
    "큐에 쌓아 순서대로 가면 안 된다.</li>"
    "</ul>"

    "<p class=foot>생성 <b>design/build_open.py</b> &middot; 데이터 <b>docs/data/deals.json</b>"
    "(서울 " + str(len(deals)) + "건 중 무대 안 " + str(len(payload)) + "곳) &middot; "
    "확정 스펙 <b>../SPEC.md</b> &sect;CH4 &middot; 근거 <b>../DECISIONS.md</b></p>"
    "</div><script>" + js + "</script></body></html>")

out = os.path.join(BASE, "open.html")
io.open(out, "w", encoding="utf-8").write(html)
print("open.html  %.1fKB" % (len(html) / 1024.0))
print("  무대 안 핀 %d개 (서울 %d건 중)" % (len(payload), len(deals)))
print("  " + " · ".join(d["ko"] for d in payload[:8]))
