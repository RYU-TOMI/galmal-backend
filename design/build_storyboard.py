# -*- coding: utf-8 -*-
"""발견 지도 스토리보드: 상태별(입장/일본확대/호버/더멀리) 정지 장면을 실제 d3-geo로 여러 장 렌더.
LOD: 축소=주요도시(major)만, 확대=소도시(minor)까지."""
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent  # design/ 의 상위 = 저장소 루트
OUT = Path(__file__).resolve().parent / "storyboard.html"

d3arr = (REPO / "docs/assets/d3-array.min.js").read_text(encoding="utf-8")
d3geo = (REPO / "docs/assets/d3-geo.min.js").read_text(encoding="utf-8")
world = (REPO / "docs/data/world.geojson").read_text(encoding="utf-8")

APP = r"""
var SVGNS="http://www.w3.org/2000/svg";
var W=560,H=380;

// tier: major(주요) / minor(소도시). haul: near/sea/far
var ORIGIN={n:'서울',lon:126.99,lat:37.55};
var CITY=[
 {n:'도쿄',lon:139.77,lat:35.68,tier:'major',haul:'near',price:'182,000',disc:'22%↓',tags:['도시','미식'],g:'linear-gradient(135deg,#ff9a76,#c6472a)'},
 {n:'오사카',lon:135.24,lat:34.69,tier:'major',haul:'near',price:'156,000',disc:'27%↓',tags:['미식','야경'],g:'linear-gradient(135deg,#f2603f,#7a2e18)'},
 {n:'후쿠오카',lon:130.45,lat:33.58,tier:'major',haul:'near',price:'119,000',disc:'31%↓',tags:['온천','가성비'],g:'linear-gradient(135deg,#ffc07a,#e0782f)'},
 {n:'삿포로',lon:141.35,lat:43.06,tier:'major',haul:'near',price:'176,000',disc:'21%↓',tags:['설경','온천'],g:'linear-gradient(135deg,#cfe6ff,#5a7fa0)'},
 {n:'오키나와',lon:127.65,lat:26.20,tier:'major',haul:'near',price:'138,000',disc:'33%↓',tags:['해변','휴양'],g:'linear-gradient(135deg,#8fe0d0,#2a8f7c)'},
 {n:'상하이',lon:121.47,lat:31.23,tier:'major',haul:'near',price:'168,000',disc:'19%↓',tags:['도시','쇼핑'],g:'linear-gradient(135deg,#7fb0b8,#2a625c)'},
 {n:'타이베이',lon:121.56,lat:25.08,tier:'major',haul:'near',price:'142,000',disc:'34%↓',tags:['야시장','가성비'],g:'linear-gradient(135deg,#ffb08a,#c6472a)'},
 {n:'나고야',lon:136.92,lat:34.86,tier:'minor',haul:'near',price:'152,000',disc:'24%↓',tags:['도시','미식'],g:'linear-gradient(135deg,#ffab8a,#b8431f)'},
 {n:'히로시마',lon:132.92,lat:34.44,tier:'minor',haul:'near',price:'134,000',disc:'30%↓',tags:['문화','미식'],g:'linear-gradient(135deg,#ffbf9a,#c6552a)'},
 {n:'가고시마',lon:130.72,lat:31.80,tier:'minor',haul:'near',price:'129,000',disc:'32%↓',tags:['온천','자연'],g:'linear-gradient(135deg,#ffcf9a,#c6652a)'},
 {n:'오이타',lon:131.74,lat:33.48,tier:'minor',haul:'near',price:'141,000',disc:'28%↓',tags:['온천','자연'],g:'linear-gradient(135deg,#ffc79a,#c65f2a)'},
 {n:'구마모토',lon:130.86,lat:32.84,tier:'minor',haul:'near',price:'137,000',disc:'29%↓',tags:['자연','온천'],g:'linear-gradient(135deg,#ffcb9a,#c6622a)'},
 {n:'다카마쓰',lon:134.02,lat:34.21,tier:'minor',haul:'near',price:'145,000',disc:'26%↓',tags:['자연','미식'],g:'linear-gradient(135deg,#ffb89a,#c6502a)'},
 {n:'마쓰야마',lon:132.70,lat:33.83,tier:'minor',haul:'near',price:'152,000',disc:'24%↓',tags:['온천','문화'],g:'linear-gradient(135deg,#ffb29a,#c64d2a)'},
 {n:'고마쓰',lon:136.41,lat:36.39,tier:'minor',haul:'near',price:'159,000',disc:'22%↓',tags:['자연','문화'],g:'linear-gradient(135deg,#ffac9a,#c6482a)'},
 {n:'방콕',lon:100.75,lat:13.69,tier:'major',haul:'sea',price:'148,000',disc:'29%↓',tags:['해변','야시장'],g:'linear-gradient(135deg,#ffd08a,#e0782f)'},
 {n:'다낭',lon:108.20,lat:16.05,tier:'major',haul:'sea',price:'163,000',disc:'26%↓',tags:['해변','휴양'],g:'linear-gradient(135deg,#9fe0c0,#2a8f6c)'},
 {n:'세부',lon:123.98,lat:10.31,tier:'major',haul:'sea',price:'171,000',disc:'23%↓',tags:['해변','스노클'],g:'linear-gradient(135deg,#8fd0e0,#2a6f8f)'},
 {n:'하노이',lon:105.80,lat:21.02,tier:'major',haul:'sea',price:'155,000',disc:'25%↓',tags:['도시','미식'],g:'linear-gradient(135deg,#ffc59a,#c65a2f)'},
 {n:'치앙마이',lon:98.97,lat:18.77,tier:'minor',haul:'sea',price:'168,000',disc:'27%↓',tags:['자연','사원'],g:'linear-gradient(135deg,#c8e6a0,#5a8f3c)'},
 {n:'푸켓',lon:98.32,lat:8.11,tier:'minor',haul:'sea',price:'189,000',disc:'23%↓',tags:['해변','휴양'],g:'linear-gradient(135deg,#8fd0e0,#2a6f8f)'},
 {n:'크라비',lon:98.99,lat:8.10,tier:'minor',haul:'sea',price:'195,000',disc:'21%↓',tags:['해변','절경'],g:'linear-gradient(135deg,#9fdcd0,#2a8f7c)'},
 {n:'푸꾸옥',lon:103.99,lat:10.17,tier:'minor',haul:'sea',price:'178,000',disc:'25%↓',tags:['해변','휴양'],g:'linear-gradient(135deg,#a8e0c0,#2a8f6c)'},
 {n:'나트랑',lon:109.22,lat:11.99,tier:'minor',haul:'sea',price:'172,000',disc:'26%↓',tags:['해변','스노클'],g:'linear-gradient(135deg,#8fe0d0,#2a8f7c)'},
 {n:'씨엠립',lon:103.81,lat:13.41,tier:'minor',haul:'sea',price:'183,000',disc:'22%↓',tags:['문화','유적'],g:'linear-gradient(135deg,#ffcf9a,#c6652a)'}
];
var LIGHT=[247,178,158],DEEP=[214,60,30];
function lerp(a,b,t){return Math.round(a+(b-a)*t);}
function num(p){return +p.replace(/[^0-9]/g,'');}

// LOD: 배율(scale)이 이 값 이상이면 지역 불문 소도시(minor)까지 표시
var MINOR_SCALE=1200;
// 장면 정의: view(줌) + 선택적 hover. minor 표시는 scale로 자동 결정.
var PANELS=[
 {t:'① 메인 입장 · 근거리 발견',s:'축소 상태 — 주요 도시만. "서울 출발" 기준 오늘 싼 곳이 한눈에.',lon:131,lat:34,scale:820},
 {t:'② 일본으로 확대',s:'확대하면 소도시까지 — 다카마쓰·마쓰야마·히로시마·규슈. 배율이 임계값을 넘으면 자동 등장.',lon:134,lat:34.4,scale:2000},
 {t:'③ 핀 호버 → 항로 + 사진 카드',s:'핀에 올리면 곡선 항로가 그려지고 사진·최저가 카드가 뜸.',lon:131,lat:35,scale:900,hover:'후쿠오카'},
 {t:'④ "더 멀리 보기" → 동남아 (축소)',s:'줌아웃하면 방콕·다낭·세부·하노이 등 주요 도시만.',lon:112,lat:16,scale:560},
 {t:'⑤ 동남아로 확대',s:'같은 규칙 — 확대하면 치앙마이·푸켓·크라비·푸꾸옥·나트랑·씨엠립까지 등장.',lon:105,lat:13,scale:1350}
];

function inB(p){return p && p[0]>=-12 && p[0]<=W+12 && p[1]>=-12 && p[1]<=H+12;}

function renderPanel(cfg){
  var fig=document.createElement('figure');fig.className='panel';
  fig.innerHTML='<figcaption><b>'+cfg.t+'</b><span>'+cfg.s+'</span></figcaption>';
  var frame=document.createElement('div');frame.className='frame';
  var svg=document.createElementNS(SVGNS,'svg');svg.setAttribute('class','map');
  svg.setAttribute('viewBox','0 0 '+W+' '+H);
  frame.appendChild(svg);fig.appendChild(frame);document.getElementById('board').appendChild(fig);

  var proj=d3.geoEquirectangular().rotate([-cfg.lon,0]).center([0,cfg.lat]).scale(cfg.scale).translate([W/2,H/2]);
  var path=d3.geoPath(proj);
  var lp=document.createElementNS(SVGNS,'path');lp.setAttribute('d',path(WORLD));lp.setAttribute('class','land');svg.appendChild(lp);

  var showMinor=cfg.scale>=MINOR_SCALE;
  var vis=CITY.filter(function(c){return (showMinor||c.tier==='major') && inB(proj([c.lon,c.lat]));});
  var vn=vis.map(function(c){return num(c.price);});
  var lo=Math.min.apply(null,vn),hi=Math.max.apply(null,vn);
  function colorOf(p){var t=1-(num(p)-lo)/((hi-lo)||1);
    return 'rgb('+lerp(LIGHT[0],DEEP[0],t)+','+lerp(LIGHT[1],DEEP[1],t)+','+lerp(LIGHT[2],DEEP[2],t)+')';}

  var O=proj([ORIGIN.lon,ORIGIN.lat]);
  var hoverCity=null;
  if(cfg.hover){for(var i=0;i<CITY.length;i++)if(CITY[i].n===cfg.hover)hoverCity=CITY[i];}
  if(hoverCity){
    var hp=proj([hoverCity.lon,hoverCity.lat]);
    var mx=(O[0]+hp[0])/2,my=(O[1]+hp[1])/2,dx=hp[0]-O[0],dy=hp[1]-O[1],len=Math.hypot(dx,dy);
    var lift=Math.min(70,len*0.28),cx=mx-dy/len*lift,cy=my+dx/len*lift;
    var arc=document.createElementNS(SVGNS,'path');arc.setAttribute('class','arc');
    arc.setAttribute('d','M'+O[0]+','+O[1]+' Q'+cx+','+cy+' '+hp[0]+','+hp[1]);svg.appendChild(arc);
  }

  var PIN=5.5;
  vis.forEach(function(c){
    var p=proj([c.lon,c.lat]),col=colorOf(c.price),act=(hoverCity&&c.n===hoverCity.n);
    var g=document.createElementNS(SVGNS,'g');g.setAttribute('class','pin'+(act?' act':''));
    g.innerHTML='<circle class="halo" cx="'+p[0]+'" cy="'+p[1]+'" r="'+(PIN*1.6)+'" fill="'+col+'"/>'+
      '<circle class="core" cx="'+p[0]+'" cy="'+p[1]+'" r="'+PIN+'" fill="'+col+'"/>'+
      '<text class="plabel'+(c.tier==='minor'?' minor':'')+'" x="'+p[0]+'" y="'+(p[1]+PIN+10)+'" text-anchor="middle">'+c.n+'</text>';
    svg.appendChild(g);
  });
  if(inB(O)){
    var og=document.createElementNS(SVGNS,'g');
    og.innerHTML='<circle class="origin-ring" cx="'+O[0]+'" cy="'+O[1]+'" r="8"/>'+
      '<circle class="origin-dot" cx="'+O[0]+'" cy="'+O[1]+'" r="3.6"/>'+
      '<text class="plabel org" x="'+O[0]+'" y="'+(O[1]-12)+'" text-anchor="middle">서울 출발</text>';
    svg.appendChild(og);
  }

  // 호버 카드(정지) 오버레이
  if(hoverCity){
    var hp2=proj([hoverCity.lon,hoverCity.lat]);
    var card=document.createElement('div');card.className='hovercard show';
    card.innerHTML='<div class="hc-photo" style="background:'+hoverCity.g+'">'+
      '<span class="ph-tag">사진 · Unsplash</span><span class="cityname">'+hoverCity.n+'</span></div>'+
      '<div class="hc-body"><div class="hc-row"><span class="hc-price"><small>\u20a9</small>'+hoverCity.price+'</span>'+
      '<span class="stamp">\ud2b9\uac00 '+hoverCity.disc+'</span></div>'+
      '<div class="hc-note">\ucd5c\uc800\uac00 \u00b7 \ud2b9\uc815\uc77c \uae30\uc900(\uacfc\uac70 \uc81c\uc678)</div>'+
      '<div class="hc-tags">'+hoverCity.tags.map(function(t){return '<span class="tag">'+t+'</span>';}).join('')+'</div>'+
      '<div class="hc-cta">\uc774 \uac00\uaca9 \ubcf4\ub7ec\uac00\uae30</div></div>';
    var leftPct=(hp2[0]/W)*100, topPct=(hp2[1]/H)*100;
    card.style.left=Math.max(18,Math.min(82,leftPct))+'%';
    card.style.top='calc('+topPct+'% - 226px)';
    frame.appendChild(card);
  }
}
PANELS.forEach(renderPanel);
"""

HTML = r"""<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>발견 지도 · 스토리보드</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css">
<style>
:root{--accent:#F2603F;--accent2:#C6472A;--ink:#20353A;--sub:#5E7A7C;
  --sea:#EDF4F3;--land:#D2E7DE;--coast:#33534F;--line:#E6EDEC;--soft:#F0F5F4;--bg:#F4F8F7;--card:#FFFFFF;}
*{box-sizing:border-box;margin:0}
body{background:var(--bg);color:var(--ink);font-family:'Pretendard Variable',Pretendard,sans-serif;-webkit-font-smoothing:antialiased;padding:30px 22px 80px}
.wrap{max-width:1200px;margin:0 auto}
h1{font-size:1.5rem;font-weight:900;letter-spacing:-.03em}
.lead{color:var(--sub);font-size:.9rem;margin:6px 0 8px;max-width:760px}
.lodkey{display:inline-flex;gap:14px;flex-wrap:wrap;font-size:.76rem;color:var(--sub);background:#fff;border:1px solid var(--line);border-radius:10px;padding:9px 13px;margin:6px 0 26px}
.lodkey b{color:var(--ink)}
.board{display:grid;grid-template-columns:repeat(2,1fr);gap:22px}
@media(max-width:820px){.board{grid-template-columns:1fr}}
.panel{background:var(--card);border:1px solid var(--line);border-radius:16px;overflow:hidden;box-shadow:0 4px 16px rgba(20,40,40,.06)}
figcaption{padding:13px 16px 11px;border-bottom:1px solid var(--line)}
figcaption b{display:block;font-size:1rem;font-weight:900;letter-spacing:-.02em}
figcaption span{display:block;font-size:.78rem;color:var(--sub);margin-top:2px;line-height:1.45}
.frame{position:relative}
svg.map{display:block;width:100%;height:auto;background:var(--sea)}
.land{fill:var(--land);stroke:#33534f22;stroke-width:.5;stroke-linejoin:round}
.arc{fill:none;stroke:var(--accent);stroke-width:1.4;stroke-linecap:round;filter:drop-shadow(0 .5px 1px #f2603f33)}
.origin-dot{fill:var(--ink)}.origin-ring{fill:none;stroke:var(--ink);stroke-width:1.4;opacity:.35}
.pin .halo{opacity:.16}.pin .core{stroke:#fff;stroke-width:1.8}.pin.act .core{stroke-width:2.6}
.plabel{font-size:11px;font-weight:800;fill:var(--ink);paint-order:stroke;stroke:var(--sea);stroke-width:2.6px;pointer-events:none}
.plabel.minor{font-size:10px;font-weight:700;fill:#4a6a66}
.plabel.org{fill:var(--ink);font-size:11px}
.hovercard{position:absolute;width:172px;background:#fff;border-radius:13px;overflow:hidden;box-shadow:0 10px 28px rgba(20,40,40,.24);border:1px solid var(--line);transform:translate(-50%,0);z-index:4}
.hc-photo{height:88px;position:relative;background-size:cover;background-position:center}
.hc-photo .cityname{position:absolute;left:10px;bottom:7px;color:#fff;font-weight:900;font-size:1rem;text-shadow:0 1px 6px #0009;letter-spacing:-.02em}
.hc-photo .ph-tag{position:absolute;right:7px;top:7px;font-size:.54rem;color:#fff9;background:#0004;border-radius:5px;padding:1px 5px}
.hc-body{padding:9px 11px 11px}.hc-row{display:flex;align-items:baseline;justify-content:space-between}
.hc-price{font-weight:900;font-size:1.2rem;color:var(--accent);letter-spacing:-.02em}.hc-price small{font-size:.7rem;font-weight:900}
.stamp{transform:rotate(-8deg);border:1.5px solid var(--accent);color:var(--accent);font-weight:900;font-size:.56rem;padding:1px 5px;border-radius:4px}
.hc-note{font-size:.6rem;color:var(--sub);margin-top:1px}
.hc-tags{display:flex;gap:4px;margin-top:7px}.tag{font-size:.58rem;background:var(--soft);border-radius:99px;padding:2px 7px;color:var(--sub);font-weight:700}
.hc-cta{margin-top:8px;background:var(--accent);color:#fff;text-align:center;font-weight:800;font-size:.7rem;border-radius:7px;padding:6px 0}
</style></head><body>
<div class="wrap">
<h1>갈래말래 · 발견 지도 스토리보드</h1>
<p class="lead">인터랙티브 대신 상태별 정지 장면. 실제 d3-geo 지도·좌표 그대로이며, 사진만 자리표시자입니다.</p>
<div class="lodkey"><span><b>LOD 규칙</b> · 축소 = 주요 도시만</span><span>확대 = 소도시(옅은 라벨)까지 등장</span><span><b>핀 색</b> = 가격(진할수록 쌈, 크기 고정)</span></div>
<div class="board" id="board"></div>
</div>
<script>__D3ARRAY__</script>
<script>__D3GEO__</script>
<script>var WORLD=__WORLD__;</script>
<script>__APP__</script>
</body></html>"""

html = (HTML.replace("__D3ARRAY__", d3arr).replace("__D3GEO__", d3geo)
        .replace("__WORLD__", world).replace("__APP__", APP))
OUT.write_text(html, encoding="utf-8")
print("생성:", OUT, "(", len(html)//1024, "KB )")
