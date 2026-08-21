# -*- coding: utf-8 -*-
"""design/stages.html 생성 — 거리 단계(B14/B4/B3) 후보안 비교.

실제 world.geojson(50m) + 실제 deals.json 좌표로 렌더한다.
d3-geo·데이터를 인라인하므로 더블클릭(파일 열기)만으로 확인 가능.

    python design/build_stages.py
"""
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "design" / "stages.html"

d3a = (ROOT / "docs/assets/d3-array.min.js").read_text(encoding="utf-8")
d3g = (ROOT / "docs/assets/d3-geo.min.js").read_text(encoding="utf-8")
world = (ROOT / "docs/data/world.geojson").read_text(encoding="utf-8")
deals = (ROOT / "docs/data/deals.json").read_text(encoding="utf-8")

# 패널 정의: (id, 제목, 부제, lon, lat, scale, LOD규칙)
#   LOD 규칙  cur = 현행(minor는 scale>=1200에서만)
#             new = 이번 단계가 연 거리대는 전부 + 이전 단계는 major만
PANELS = [
    ("p1", "현행", "center 78°E · scale 230 · 현행 LOD", 78, 30, 230, "cur", 2),
    ("p2", "A안 — 중심만 이동", "center 122°E · scale 200 · 현행 LOD", 122, 30, 200, "cur", 2),
    ("p3", "B안 — 중심 이동 + LOD 개편", "center 122°E · scale 190 · 새 LOD", 122, 14, 190, "new", 2),
    ("p4", "C안 — 더 축소", "center 122°E · scale 165 · 새 LOD", 122, 14, 165, "new", 2),
]

STAGES3 = [
    ("s0", "가까운 곳", "center 132°E · scale 1500", 132, 35.5, 1500, "new", 0),
    ("s1", "＋동남아", "center 117°E · scale 720", 117, 19, 720, "new", 1),
    ("s2", "＋유럽·미주", "center 122°E · scale 190", 122, 14, 190, "new", 2),
]

HTML = """<!doctype html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>갈래말래 — 거리 단계 후보안</title>
<style>
:root{--accent:#F2603F;--accent2:#C6472A;--ink:#20353A;--sub:#5E7A7C;
 --sea:#EDF4F3;--land:#D2E7DE;--coast:#33534F;--line:#E6EDEC;--soft:#F0F5F4;--card:#FFF;--bg:#F4F8F7}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
 font-family:Pretendard,-apple-system,"Segoe UI","Malgun Gothic",sans-serif;line-height:1.6}
.wrap{max-width:1240px;margin:0 auto;padding:44px 22px 90px}
h1{font-weight:900;letter-spacing:-.035em;font-size:2.3rem;margin:0 0 8px}
h1 em{font-style:normal;color:var(--accent)}
.lede{color:var(--sub);max-width:66ch;margin:0 0 12px}
h2{font-weight:900;font-size:1.28rem;letter-spacing:-.02em;margin:52px 0 6px}
h2 .n{color:var(--accent);margin-right:8px}
.note{color:var(--sub);font-size:.9rem;margin:0 0 18px;max-width:74ch}
.panel{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:20px}
.grid{display:grid;gap:18px}
@media(min-width:900px){.g2{grid-template-columns:1fr 1fr}.g3{grid-template-columns:repeat(3,1fr)}}
.card{background:var(--card);border:1px solid var(--line);border-radius:16px;overflow:hidden}
.card.win{border-color:var(--accent);box-shadow:0 0 0 2px rgba(242,96,63,.14)}
.card h3{margin:0;padding:13px 16px 2px;font-size:1rem;font-weight:900;letter-spacing:-.02em;
 display:flex;align-items:center;gap:8px}
.badge{font-size:.62rem;font-weight:900;padding:2px 8px;border-radius:99px;background:var(--accent);color:#fff}
.badge.bad{background:var(--sub)}
.card .sub{padding:0 16px 10px;font-size:.72rem;color:var(--sub);font-weight:700;
 font-variant-numeric:tabular-nums}
.mapbox{position:relative;background:var(--sea);border-top:1px solid var(--line);
 border-bottom:1px solid var(--line)}
svg.map{display:block;width:100%;height:auto}
.land{fill:var(--land);stroke:var(--coast);stroke-width:.5;stroke-linejoin:round}
.pin .core{stroke:#fff;stroke-width:1.6}
.pin .halo{opacity:.16}
.plabel{font-size:9px;font-weight:800;fill:var(--ink);paint-order:stroke;
 stroke:var(--sea);stroke-width:2.4px;pointer-events:none}
.plabel.minor{font-size:8px;font-weight:700;fill:#4a6a66}
.org .ring{fill:none;stroke:var(--accent);stroke-width:1.6}
.org .dot{fill:var(--accent)}
.arc{fill:none;stroke:var(--accent);stroke-width:1;opacity:.32}
.cropzone{fill:#20353A;opacity:.13}
.cropline{stroke:#20353A;stroke-width:1;stroke-dasharray:4 3;opacity:.4}
.stat{padding:11px 16px 14px;font-size:.78rem;display:flex;flex-wrap:wrap;gap:6px 14px}
.stat b{font-variant-numeric:tabular-nums}
.ok{color:#1E7A50;font-weight:800}
.bad{color:var(--accent2);font-weight:800}
.miss{padding:0 16px 14px;font-size:.72rem;color:var(--accent2);font-weight:700}
table{width:100%;border-collapse:collapse;font-size:.88rem}
th{text-align:left;font-weight:700;font-size:.76rem;color:var(--sub);padding:0 10px 9px;
 border-bottom:1px solid var(--line)}
td{padding:11px 10px;border-bottom:1px solid var(--line);vertical-align:top}
tr:last-child td{border-bottom:0}
code{font-family:ui-monospace,Consolas,monospace;font-size:.85em;background:var(--soft);
 padding:1px 5px;border-radius:4px}
.legend{display:flex;gap:16px;flex-wrap:wrap;font-size:.76rem;color:var(--sub);margin:14px 0 0}
.legend i{display:inline-block;width:11px;height:11px;border-radius:99px;background:var(--accent);
 margin-right:5px;vertical-align:-1px}
.legend .crp{width:14px;height:11px;border-radius:2px;background:#20353A;opacity:.18}
.foot{margin-top:60px;padding-top:18px;border-top:1px solid var(--line);font-size:.8rem;color:var(--sub)}
ul.k{margin:8px 0 0;padding-left:18px;font-size:.88rem;color:var(--sub)}
ul.k li{margin:6px 0}ul.k b{color:var(--ink)}
.warn{background:var(--soft);border-radius:11px;padding:12px 14px;font-size:.85rem;color:var(--sub);margin-top:14px}
.warn b{color:var(--ink)}
</style></head><body><div class="wrap">

<h1>거리 단계 — <em>후보안 비교</em></h1>
<p class="lede"><code>＋유럽·미주</code>를 눌렀는데 피드에 있는 로스앤젤레스·호놀룰루가 지도에 없다.
원인을 파 보니 <b>서로 다른 문제 세 개가 겹쳐</b> 있었다. 실제 해안선(50m)과 실제 딜 좌표로 그렸다.</p>

<h2><span class="n">01</span>원인은 하나가 아니다</h2>
<p class="note">각각 다른 장치가 필요하다. 하나만 고치면 나머지가 남는다.</p>
<div class="panel"><table>
<thead><tr><th style="width:16%">문제</th><th style="width:42%">내용</th><th>고치는 방법</th></tr></thead>
<tbody>
<tr><td><b>① 투영 범위</b><br><span style="color:var(--sub);font-size:.8rem">B14</span></td>
<td>far 중심이 <code>78°E</code>라 <b>44° 서쪽으로 치우쳐</b> 있다. 왼쪽은 딜이 0건인 아프리카·대서양에 쓰고,
오른쪽에서 미주가 잘린다.</td>
<td>중심을 <b>122°E</b>로. 모든 딜을 감싸는 최소 호가 <b>239.5°</b>이고 그 중심이 121.8°E다.</td></tr>
<tr><td><b>② LOD 규칙</b><br><span style="color:var(--sub);font-size:.8rem">B4 — 더 크다</span></td>
<td><code>MINOR_SCALE=1200</code>이라 far(230)에서 <b>minor가 전부 숨는다.</b>
서울 장거리 딜 20건 중 <b>12건이 minor</b> → 유럽·미주 단계인데 유럽·미주가 안 보인다.</td>
<td><b>이번 단계가 연 거리대는 전부 표시</b>, 이전 단계 것만 major로 추린다.</td></tr>
<tr><td><b>③ 라벨 겹침</b><br><span style="color:var(--sub);font-size:.8rem">B3·B15</span></td>
<td>홍콩·선전·마카오가 <b>1.1~1.4px</b> 안에 뭉친다. <b>배율을 어떻게 바꿔도 안 풀린다</b> — 지리적 사실이다.</td>
<td>배율이 아니라 <b>겹침 회피 + 가장자리 클램프</b>라는 별도 규칙.</td></tr>
</tbody></table>
<div class="warn">덧붙여 지도는 <code>preserveAspectRatio="xMidYMid slice"</code>라 <b>좌우가 잘린다.</b>
아래 지도의 <span style="background:#20353A;opacity:.5;color:#fff;padding:0 5px;border-radius:3px">어두운 띠</span>가
1280×800 창에서 <b>실제로 안 보이는 영역</b>이다. 창이 좁고 높을수록 더 잘린다.</div>
</div>

<h2><span class="n">02</span>후보안 — 같은 데이터, 같은 축척 비교</h2>
<p class="note">서울 출발 · <code>＋유럽·미주</code> 단계. 핀 색이 진할수록 싸다(실제 앱과 동일).</p>
<div class="grid g2" id="panels"></div>
<div class="legend">
  <span><i></i>표시되는 딜</span>
  <span><span class="crp"></span>1280×800에서 잘리는 영역</span>
  <span>얇은 선 = 서울에서의 항로</span>
</div>

<h2><span class="n">03</span>권장 — B안</h2>
<p class="note">A안은 미주를 되찾지만 <b>장거리 딜 20건 중 8건만</b> 그린다(②를 안 고쳤으므로).
C안은 여유가 크지만 한국이 작아지고 아시아가 더 뭉친다. <b>B안이 전부 담으면서 축척 손해가 가장 적다.</b></p>
<div class="panel">
<table><thead><tr><th>항목</th><th>현행</th><th>A안</th><th style="color:var(--accent)">B안</th><th>C안</th></tr></thead>
<tbody id="cmp"></tbody></table>
</div>

<h2><span class="n">04</span>B안으로 본 3단계 전체</h2>
<p class="note">단계가 바뀌면 무엇이 새로 열리는지. 새 LOD 규칙 적용.</p>
<div class="grid g3" id="stages"></div>

<h2><span class="n">05</span>B안을 골라도 남는 것</h2>
<div class="panel">
<ul class="k">
<li><b>라벨 겹침(③)은 그대로 남는다.</b> 홍콩·선전·마카오·광저우는 어떤 배율에서도 붙는다.
    <b>겹침 회피 규칙을 따로 정해야 한다</b> — 그게 B3/B15다.</li>
<li><b>가장자리 클램프</b>도 필요하다. 바르셀로나·호놀룰루가 가장자리 가까이 오므로 라벨이 잘린다.</li>
<li><b>필터 도크가 우측 하단 핀을 가린다</b>(B16). B안에서는 그 자리가 오세아니아·뉴질랜드다.</li>
<li><b>단계 이름</b>: 지금 <code>＋유럽·미주</code>인데 실제로는 중동·오세아니아도 들어온다.
    이름을 데이터에 맞출지 결정해야 한다(문구는 <code>COPY.md</code>).</li>
</ul>
</div>

<p class="foot">확정 스펙: <b>../SPEC.md</b> §CH1 · 판단 근거: <b>../DECISIONS.md</b> ·
재생성: <code>python design/build_stages.py</code><br>
실제 <code>world.geojson</code>(50m, 182 features)과 커밋된 <code>deals.json</code>으로 렌더했다. 더미 데이터 없음.</p>

</div>

<script>__D3A__</script>
<script>__D3G__</script>
<script>
var WORLD=__WORLD__, DEALS=__DEALS__;
var W=1000,H=680,PANELS=__PANELS__,STAGES=__STAGES__,CROP=0.86;
var H2S={short:0,mid:1,long:2};
var SEL=DEALS.deals.filter(function(d){return d.o==="SEL";});
var ORG=DEALS.origins.SEL;
var NS="http://www.w3.org/2000/svg";
function el(n,a){var e=document.createElementNS(NS,n);for(var k in a)e.setAttribute(k,a[k]);return e;}

function shown(cfg){
  return SEL.filter(function(d){
    var s=H2S[d.haul];
    if(s>cfg.si) return false;
    if(cfg.lod==="cur") return cfg.scale>=1200 || d.tier==="major";
    return s===cfg.si ? true : d.tier==="major";   // new
  });
}
function colorOf(list){
  var ps=list.map(function(d){return d.price;});
  var lo=Math.min.apply(null,ps),hi=Math.max.apply(null,ps),r=hi-lo||1;
  return function(p){var t=1-(p-lo)/r;   // 쌀수록 진하게
    var a=[247,178,158],b=[214,60,30];
    return "rgb("+a.map(function(v,i){return Math.round(v+(b[i]-v)*t);}).join(",")+")";};
}
function build(cfg,host,showStats){
  var proj=d3.geoEquirectangular().rotate([-cfg.lon,0]).center([0,cfg.lat])
             .scale(cfg.scale).translate([W/2,H/2]);
  var path=d3.geoPath(proj);
  var svg=el("svg",{class:"map",viewBox:"0 0 "+W+" "+H,preserveAspectRatio:"xMidYMid meet"});
  svg.appendChild(el("rect",{x:0,y:0,width:W,height:H,fill:"var(--sea)"}));
  svg.appendChild(el("path",{class:"land",d:path(WORLD)}));

  var list=shown(cfg), col=colorOf(list.length?list:SEL);
  var O=proj([ORG.lon,ORG.lat]);
  var inside=0, out=[];
  list.forEach(function(d){
    var p=proj([d.lon,d.lat]);
    var vis=p&&p[0]>=0&&p[0]<=W&&p[1]>=0&&p[1]<=H;
    if(!vis){out.push(d.ko);return;}
    inside++;
    var g=el("g",{class:"pin"});
    g.appendChild(el("circle",{class:"halo",cx:p[0],cy:p[1],r:7,fill:col(d.price)}));
    g.appendChild(el("circle",{class:"core",cx:p[0],cy:p[1],r:4.4,fill:col(d.price)}));
    var t=el("text",{class:"plabel"+(d.tier==="minor"?" minor":""),x:p[0],y:p[1]+13,"text-anchor":"middle"});
    t.textContent=d.ko; g.appendChild(t); svg.appendChild(g);
    if(O){var mx=(O[0]+p[0])/2,my=(O[1]+p[1])/2-Math.abs(p[0]-O[0])*0.14;
      svg.appendChild(el("path",{class:"arc",d:"M"+O[0]+","+O[1]+" Q"+mx+","+my+" "+p[0]+","+p[1]}));}
  });
  if(O){var g2=el("g",{class:"org"});
    g2.appendChild(el("circle",{class:"ring",cx:O[0],cy:O[1],r:6}));
    g2.appendChild(el("circle",{class:"dot",cx:O[0],cy:O[1],r:2.6}));
    svg.appendChild(g2);}
  // 크롭 영역
  var cw=W*(1-CROP)/2;
  svg.appendChild(el("rect",{class:"cropzone",x:0,y:0,width:cw,height:H}));
  svg.appendChild(el("rect",{class:"cropzone",x:W-cw,y:0,width:cw,height:H}));
  svg.appendChild(el("line",{class:"cropline",x1:cw,y1:0,x2:cw,y2:H}));
  svg.appendChild(el("line",{class:"cropline",x1:W-cw,y1:0,x2:W-cw,y2:H}));

  var box=document.createElement("div"); box.className="mapbox"; box.appendChild(svg);
  host.appendChild(box);

  if(showStats){
    var up=SEL.filter(function(d){return H2S[d.haul]<=cfg.si;});
    var lo=list.filter(function(d){return d.haul==="long";});
    var loAll=up.filter(function(d){return d.haul==="long";});
    var st=document.createElement("div"); st.className="stat";
    st.innerHTML='<span>그리는 딜 <b>'+list.length+'</b>/'+up.length+'</span>'+
      '<span>장거리 <b class="'+(lo.length===loAll.length?"ok":"bad")+'">'+lo.length+'/'+loAll.length+'</b></span>'+
      '<span>화면 밖 <b class="'+(out.length?"bad":"ok")+'">'+out.length+'</b></span>';
    host.appendChild(st);
    if(out.length){var m=document.createElement("div");m.className="miss";
      m.textContent="✗ 화면 밖: "+out.join(", ");host.appendChild(m);}
  }
  return {list:list,out:out};
}

var res={};
PANELS.forEach(function(c,i){
  var card=document.createElement("div"); card.className="card"+(c.id==="p3"?" win":"");
  var h=document.createElement("h3"); h.textContent=c.title;
  if(c.id==="p3"){var b=document.createElement("span");b.className="badge";b.textContent="권장";h.appendChild(b);}
  if(c.id==="p1"){var b2=document.createElement("span");b2.className="badge bad";b2.textContent="현행";h.appendChild(b2);}
  card.appendChild(h);
  var s=document.createElement("div"); s.className="sub"; s.textContent=c.sub; card.appendChild(s);
  res[c.id]=build(c,card,true);
  document.getElementById("panels").appendChild(card);
});

// 비교표
var rows=[
 ["중심 경도",function(c){return c.lon+"°E";}],
 ["배율",function(c){return c.scale;}],
 ["그리는 딜",function(c,r){var up=SEL.filter(function(d){return H2S[d.haul]<=c.si;});return r.list.length+" / "+up.length;}],
 ["장거리 딜",function(c,r){var loAll=SEL.filter(function(d){return d.haul==="long";});
    var lo=r.list.filter(function(d){return d.haul==="long";});
    return '<b class="'+(lo.length===loAll.length?"ok":"bad")+'">'+lo.length+" / "+loAll.length+"</b>";}],
 ["화면 밖",function(c,r){return '<b class="'+(r.out.length?"bad":"ok")+'">'+r.out.length+"곳</b>";}]
];
var tb=document.getElementById("cmp");
rows.forEach(function(r){
  var tr=document.createElement("tr");
  tr.innerHTML="<td><b>"+r[0]+"</b></td>"+PANELS.map(function(c){
    return "<td>"+r[1](c,res[c.id])+"</td>";}).join("");
  tb.appendChild(tr);
});

// 3단계
STAGES.forEach(function(c){
  var card=document.createElement("div"); card.className="card";
  var h=document.createElement("h3"); h.textContent=c.title; card.appendChild(h);
  var s=document.createElement("div"); s.className="sub"; s.textContent=c.sub; card.appendChild(s);
  build(c,card,true);
  document.getElementById("stages").appendChild(card);
});
</script>
</body></html>
"""


def js(panels):
    return json.dumps([
        {"id": p[0], "title": p[1], "sub": p[2], "lon": p[3],
         "lat": p[4], "scale": p[5], "lod": p[6], "si": p[7]}
        for p in panels], ensure_ascii=False)


out = (HTML
       .replace("__D3A__", d3a)
       .replace("__D3G__", d3g)
       .replace("__WORLD__", world)
       .replace("__DEALS__", deals)
       .replace("__PANELS__", js(PANELS))
       .replace("__STAGES__", js(STAGES3)))
OUT.write_text(out, encoding="utf-8")
print(f"생성: {OUT}  ({len(out)/1024:.0f}KB)")
