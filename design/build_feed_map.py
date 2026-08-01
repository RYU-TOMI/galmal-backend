# -*- coding: utf-8 -*-
"""지도 메인 + '오늘의 발견' 카드 피드(레일) 얹기 + 카드<->지도 양방향 연동.
lean-back(카드만 훑기) + lean-forward(지도 탐색) 공존. d3-geo/world 인라인 → file:// 동작."""
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent  # design/ 의 상위 = 저장소 루트
OUT = Path(__file__).resolve().parent / "feed_map.html"

d3arr = (REPO / "docs/assets/d3-array.min.js").read_text(encoding="utf-8")
d3geo = (REPO / "docs/assets/d3-geo.min.js").read_text(encoding="utf-8")
world = (REPO / "docs/data/world.geojson").read_text(encoding="utf-8")

APP = r"""
var SVGNS="http://www.w3.org/2000/svg";
var W=1000,H=680;
var MINOR_SCALE=1200;
var VIEWS={near:{lon:132,lat:35.5,scale:1500},sea:{lon:117,lat:19,scale:720},far:{lon:78,lat:30,scale:230}};
var STAGES=['near','sea','far'];var stageIdx=0;

var ORIGIN={n:'서울',lon:126.99,lat:37.55};
// when=상대라벨, date=실제 출발~귀국(요일), nights=박수
var CITY=[
 {n:'후쿠오카',lon:130.45,lat:33.58,tier:'major',haul:'near',price:'119,000',disc:'31%↓',when:'이번 주말',date:'8/8(금)~8/10(일)',nights:'2박3일',why:'평소보다 31%↓ · 직항 5만원대',tags:['온천','가성비'],g:'linear-gradient(135deg,#ffc07a,#e0782f)'},
 {n:'오키나와',lon:127.65,lat:26.20,tier:'major',haul:'near',price:'138,000',disc:'33%↓',when:'광복절 연휴',date:'8/15(토)~8/18(화)',nights:'3박4일',why:'연휴인데 급특가 떴어요',tags:['해변','휴양'],g:'linear-gradient(135deg,#8fe0d0,#2a8f7c)'},
 {n:'타이베이',lon:121.56,lat:25.08,tier:'major',haul:'near',price:'142,000',disc:'34%↓',when:'3주 뒤',date:'8/22(금)~8/25(월)',nights:'3박4일',why:'야시장 시즌 · 최근 최저',tags:['야시장','가성비'],g:'linear-gradient(135deg,#ffb08a,#c6472a)'},
 {n:'오사카',lon:135.24,lat:34.69,tier:'major',haul:'near',price:'156,000',disc:'27%↓',when:'다음 달',date:'9/4(금)~9/7(월)',nights:'3박4일',why:'비수기 저점 구간',tags:['미식','야경'],g:'linear-gradient(135deg,#f2603f,#7a2e18)'},
 {n:'상하이',lon:121.47,lat:31.23,tier:'major',haul:'near',price:'168,000',disc:'19%↓',when:'이번 달 말',date:'8/29(토)~8/31(월)',nights:'2박3일',why:'무비자 이후 첫 특가',tags:['도시','쇼핑'],g:'linear-gradient(135deg,#7fb0b8,#2a625c)'},
 {n:'삿포로',lon:141.35,lat:43.06,tier:'major',haul:'near',price:'176,000',disc:'21%↓',when:'다음 달',date:'9/12(금)~9/15(월)',nights:'3박4일',why:'가을 초입 반짝 하락',tags:['설경','온천'],g:'linear-gradient(135deg,#cfe6ff,#5a7fa0)'},
 {n:'도쿄',lon:139.77,lat:35.68,tier:'major',haul:'near',price:'182,000',disc:'22%↓',when:'3주 뒤',date:'8/20(수)~8/23(토)',nights:'3박4일',why:'주중 출발이 특히 쌈',tags:['도시','미식'],g:'linear-gradient(135deg,#ff9a76,#c6472a)'},
 {n:'다카마쓰',lon:134.02,lat:34.21,tier:'minor',haul:'near',price:'145,000',disc:'26%↓',when:'다음 달',date:'9/5(금)~9/8(월)',nights:'3박4일',why:'우동 성지 · 소도시 직항',tags:['자연','미식'],g:'linear-gradient(135deg,#ffb89a,#c6502a)'},
 {n:'가고시마',lon:130.72,lat:31.80,tier:'minor',haul:'near',price:'129,000',disc:'32%↓',when:'광복절 연휴',date:'8/14(목)~8/17(일)',nights:'3박4일',why:'온천+화산 · 근거리 최저권',tags:['온천','자연'],g:'linear-gradient(135deg,#ffcf9a,#c6652a)'},
 {n:'방콕',lon:100.75,lat:13.69,tier:'major',haul:'sea',price:'148,000',disc:'29%↓',when:'개천절 연휴',date:'10/3(토)~10/7(수)',nights:'4박5일',why:'건기 시작 · 지금이 딱',tags:['해변','야시장'],g:'linear-gradient(135deg,#ffd08a,#e0782f)'},
 {n:'다낭',lon:108.20,lat:16.05,tier:'major',haul:'sea',price:'163,000',disc:'26%↓',when:'다음 달',date:'9/25(금)~9/28(월)',nights:'3박4일',why:'우기 전 마지막 특가',tags:['해변','휴양'],g:'linear-gradient(135deg,#9fe0c0,#2a8f6c)'},
 {n:'세부',lon:123.98,lat:10.31,tier:'major',haul:'sea',price:'171,000',disc:'23%↓',when:'한글날 연휴',date:'10/9(금)~10/12(월)',nights:'3박4일',why:'스노클 시즌 진입',tags:['해변','스노클'],g:'linear-gradient(135deg,#8fd0e0,#2a6f8f)'},
 {n:'치앙마이',lon:98.97,lat:18.77,tier:'minor',haul:'sea',price:'168,000',disc:'27%↓',when:'11월 초',date:'11/6(금)~11/9(월)',nights:'3박4일',why:'선선한 시즌 · 소도시 특가',tags:['자연','사원'],g:'linear-gradient(135deg,#c8e6a0,#5a8f3c)'}
];
var LIGHT=[247,178,158],DEEP=[214,60,30];
function lerp(a,b,t){return Math.round(a+(b-a)*t);}
function num(p){return +p.replace(/[^0-9]/g,'');}

var svg=document.getElementById('map');svg.setAttribute('viewBox','0 0 '+W+' '+H);
var proj=d3.geoEquirectangular().translate([W/2,H/2]);
var path=d3.geoPath(proj);
var landPath=document.createElementNS(SVGNS,'path');landPath.setAttribute('class','land');
document.getElementById('lands').appendChild(landPath);
var arc=document.getElementById('arc');
var pins=document.getElementById('pins');
var og=document.getElementById('origin');
var feed=document.getElementById('feed');
var stageEl=document.querySelector('.stage');
var hc=document.getElementById('hc');
var active=null;
function svgToClient(x,y){var pt=svg.createSVGPoint();pt.x=x;pt.y=y;return pt.matrixTransform(svg.getScreenCTM());}

function visibleCities(){var upto=STAGES.slice(0,stageIdx+1),showMinor=VIEWS[STAGES[stageIdx]].scale>=MINOR_SCALE,out=[];
  CITY.forEach(function(c,i){if(upto.indexOf(c.haul)>=0&&(showMinor||c.tier==='major')){c._i=i;out.push(c);}});
  out.sort(function(a,b){return num(a.price)-num(b.price);});return out;}

function colorMaker(vis){var vn=vis.map(function(c){return num(c.price);});
  var lo=Math.min.apply(null,vn),hi=Math.max.apply(null,vn);
  return function(p){var t=1-(num(p)-lo)/((hi-lo)||1);
    return 'rgb('+lerp(LIGHT[0],DEEP[0],t)+','+lerp(LIGHT[1],DEEP[1],t)+','+lerp(LIGHT[2],DEEP[2],t)+')';};}

var PIN_R=6;
function render(){
  var v=VIEWS[STAGES[stageIdx]];
  proj.rotate([-v.lon,0]).center([0,v.lat]).scale(v.scale).translate([W/2,H/2]);
  landPath.setAttribute('d',path(WORLD));
  var O=proj([ORIGIN.lon,ORIGIN.lat]);ORIGIN.x=O[0];ORIGIN.y=O[1];
  og.innerHTML='<circle class="origin-ring" cx="'+O[0]+'" cy="'+O[1]+'" r="9"/>'+
    '<circle class="origin-dot" cx="'+O[0]+'" cy="'+O[1]+'" r="4"/>'+
    '<text class="plabel org" x="'+O[0]+'" y="'+(O[1]-13)+'" text-anchor="middle">서울 출발</text>';
  var vis=visibleCities();var colorOf=colorMaker(vis);
  vis.forEach(function(c){var p=proj([c.lon,c.lat]);c.x=p[0];c.y=p[1];c._col=colorOf(c.price);});
  // 핀
  pins.innerHTML='';
  vis.forEach(function(c){
    var g=document.createElementNS(SVGNS,'g');g.setAttribute('class','pin');g.dataset.i=c._i;
    g.innerHTML='<circle class="halo" cx="'+c.x+'" cy="'+c.y+'" r="'+(PIN_R*1.6)+'" fill="'+c._col+'"/>'+
      '<circle class="core" cx="'+c.x+'" cy="'+c.y+'" r="'+PIN_R+'" fill="'+c._col+'"/>'+
      '<text class="plabel'+(c.tier==='minor'?' minor':'')+'" x="'+c.x+'" y="'+(c.y+PIN_R+11)+'" text-anchor="middle">'+c.n+'</text>';
    (function(el,i){el.addEventListener('mouseenter',function(){highlight(i,false);});
      el.addEventListener('click',function(e){e.stopPropagation();highlight(i,true);});})(g,c._i);
    pins.appendChild(g);
  });
  // 카드 피드
  feed.innerHTML='<div class="feedhead"><b>오늘의 발견</b><span>서울 출발 · 3일 이내 · '+vis.length+'곳</span></div>';
  vis.forEach(function(c,idx){
    var hero=idx===0;
    var card=document.createElement('div');card.className='fcard'+(hero?' hero':'');card.dataset.i=c._i;
    card.innerHTML=
      '<div class="thumb" style="background:'+c.g+'">'+(hero?'<span class="pick">오늘의 한 방</span>':'')+'</div>'+
      '<div class="fbody"><div class="frow"><b class="fcity">'+c.n+'</b><span class="stamp">'+c.disc+'</span></div>'+
      '<div class="fprice"><small>₩</small>'+c.price+' <span class="tilde">~</span></div>'+
      '<div class="fdate"><span class="when">'+c.when+'</span>'+c.date+' · '+c.nights+'</div>'+
      '<div class="fwhy">'+c.why+'</div>'+
      '<div class="ftags">'+c.tags.map(function(t){return '<span class="tag">'+t+'</span>';}).join('')+'</div>'+
      (hero?'<div class="gorow"><button class="go">갈래 →</button><button class="skip">말래</button></div>':'')+
      '</div>';
    (function(el,i){el.addEventListener('mouseenter',function(){highlight(i,false);});
      el.addEventListener('click',function(){highlight(i,true);});})(card,c._i);
    feed.appendChild(card);
  });
  if(active!==null)paintActive();
}

function cityByI(i){for(var k=0;k<CITY.length;k++)if(CITY[k]._i===i&&CITY[k].x!=null)return CITY[k];
  return CITY[i];}
function paintActive(){
  var ps=document.querySelectorAll('.pin');for(var k=0;k<ps.length;k++)ps[k].classList.toggle('act',+ps[k].dataset.i===active);
  var cs=document.querySelectorAll('.fcard');for(var j=0;j<cs.length;j++)cs[j].classList.toggle('on',+cs[j].dataset.i===active);
}
function highlight(i,scroll){
  active=i;var c=cityByI(i);paintActive();
  if(c&&c.x!=null){
    var mx=(ORIGIN.x+c.x)/2,my=(ORIGIN.y+c.y)/2,dx=c.x-ORIGIN.x,dy=c.y-ORIGIN.y,len=Math.hypot(dx,dy)||1;
    var lift=Math.min(90,len*0.24),cx=mx-dy/len*lift,cy=my+dx/len*lift;
    arc.setAttribute('d','M'+ORIGIN.x+','+ORIGIN.y+' Q'+cx+','+cy+' '+c.x+','+c.y);
    var L=arc.getTotalLength();arc.style.transition='none';arc.style.strokeDasharray=L;arc.style.strokeDashoffset=L;
    arc.getBoundingClientRect();arc.style.transition='stroke-dashoffset .42s ease';arc.style.strokeDashoffset=0;
    // 지도 위 플로팅 카드(항로 끝)
    hc.innerHTML='<div class="hc-photo" style="background:'+c.g+'"><span class="ph-tag">사진 · Unsplash</span>'+
      '<span class="cityname">'+c.n+'</span></div><div class="hc-body">'+
      '<div class="hc-row"><span class="hc-price"><small>₩</small>'+c.price+' <span class="tilde">~</span></span>'+
      '<span class="stamp">특가 '+c.disc+'</span></div>'+
      '<div class="hc-why">'+c.why+'</div>'+
      '<div class="hc-tags">'+c.tags.map(function(t){return '<span class="tag">'+t+'</span>';}).join('')+'</div>'+
      '<div class="hc-cta">갈래 → 예약 보기</div></div>';
    var cp=svgToClient(c.x,c.y),box=stageEl.getBoundingClientRect();
    var left=cp.x-box.left,top=cp.y-box.top-16-214;
    if(top<8)top=cp.y-box.top+20;
    left=Math.max(98,Math.min(box.width-98,left));
    hc.style.left=left+'px';hc.style.top=top+'px';hc.classList.add('show');
  }
  if(scroll){var card=document.querySelector('.fcard[data-i="'+i+'"]');if(card)card.scrollIntoView({behavior:'smooth',block:'nearest'});}
}
function clearHi(){active=null;paintActive();hc.classList.remove('show');
  if(arc.getTotalLength){arc.style.transition='stroke-dashoffset .2s ease';arc.style.strokeDashoffset=arc.getTotalLength();}}

function setStage(idx){stageIdx=idx;clearHi();render();
  var bs=document.querySelectorAll('.stagebar .pill');for(var k=0;k<bs.length;k++)bs[k].classList.toggle('on',k===idx);}
var bs=document.querySelectorAll('.stagebar .pill');
for(var b=0;b<bs.length;b++){(function(el,idx){el.addEventListener('click',function(){setStage(idx);});})(bs[b],b);}
stageEl.addEventListener('mouseleave',function(){if(matchMedia('(hover:hover)').matches)clearHi();});
svg.addEventListener('click',function(e){if(e.target===svg||e.target.classList.contains('land'))clearHi();});
render();
"""

HTML = r"""<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>지도 + 카드 피드</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css">
<style>
:root{--accent:#F2603F;--accent2:#C6472A;--ink:#20353A;--sub:#5E7A7C;
  --sea:#EDF4F3;--land:#D2E7DE;--coast:#33534F;--line:#E6EDEC;--soft:#F0F5F4;--bg:#F4F8F7;--card:#FFFFFF;}
*{box-sizing:border-box;margin:0}
html,body{height:100%}
body{background:var(--bg);color:var(--ink);font-family:'Pretendard Variable',Pretendard,sans-serif;-webkit-font-smoothing:antialiased;display:flex;flex-direction:column}
.hdr{display:flex;align-items:center;height:56px;padding:0 18px;background:var(--card);border-bottom:1px solid var(--line);flex:0 0 auto}
.logo{font-weight:900;letter-spacing:-.03em;font-size:1.25rem}.logo em{font-style:normal;color:var(--accent)}
.nav{display:flex;gap:4px;margin-left:26px;font-size:.85rem;color:var(--sub);font-weight:600}.nav .on{color:var(--ink);font-weight:800}
.tools{margin-left:auto;display:flex;gap:7px}
.pill{border:1.5px solid var(--line);border-radius:99px;padding:6px 12px;font-size:.78rem;color:var(--sub);background:#fff;font-weight:700;cursor:pointer}
.pill.on{background:var(--accent);color:#fff;border-color:var(--accent)}
.layout{flex:1 1 auto;display:flex;min-height:0}
/* 카드 피드 레일 */
.feed{flex:0 0 340px;overflow-y:auto;padding:14px;background:var(--bg);border-right:1px solid var(--line);display:flex;flex-direction:column;gap:10px}
.feedhead{display:flex;justify-content:space-between;align-items:baseline;padding:2px 2px 4px}
.feedhead b{font-size:1.05rem;font-weight:900;letter-spacing:-.02em}.feedhead span{font-size:.7rem;color:var(--sub)}
.fcard{display:flex;gap:11px;background:#fff;border:1.5px solid var(--line);border-radius:13px;padding:10px;cursor:pointer;transition:border-color .12s,box-shadow .12s,transform .12s}
.fcard:hover,.fcard.on{border-color:var(--accent);box-shadow:0 6px 18px rgba(242,96,63,.16);transform:translateY(-1px)}
.thumb{flex:0 0 62px;height:62px;border-radius:10px;position:relative;background-size:cover}
.fcard.hero{flex-direction:column;gap:0}
.fcard.hero .thumb{width:100%;height:104px;margin-bottom:9px}
.pick{position:absolute;left:8px;top:8px;background:#fff;color:var(--accent);font-weight:900;font-size:.6rem;padding:2px 7px;border-radius:99px;box-shadow:0 2px 6px #0002}
.fbody{flex:1;min-width:0}
.frow{display:flex;justify-content:space-between;align-items:center}
.fcity{font-size:.98rem;font-weight:900;letter-spacing:-.02em}
.stamp{transform:rotate(-7deg);border:1.5px solid var(--accent);color:var(--accent);font-weight:900;font-size:.56rem;padding:1px 5px;border-radius:4px}
.fprice{font-weight:900;font-size:1.12rem;color:var(--accent);letter-spacing:-.02em;margin-top:2px}.fprice small{font-size:.66rem}
.tilde{font-size:.66rem;color:var(--sub);font-weight:700}
.fdate{display:flex;align-items:center;gap:6px;flex-wrap:wrap;margin-top:5px;font-size:.74rem;font-weight:800;color:var(--ink)}
.when{background:var(--accent);color:#fff;font-weight:800;font-size:.62rem;padding:2px 8px;border-radius:99px}
.fwhy{font-size:.72rem;color:var(--sub);margin-top:5px;line-height:1.4}
.ftags{display:flex;gap:4px;margin-top:7px}.tag{font-size:.6rem;background:var(--soft);border-radius:99px;padding:2px 7px;color:var(--sub);font-weight:700}
.gorow{display:flex;gap:7px;margin-top:11px}
.go{flex:1;background:var(--accent);color:#fff;border:0;font-weight:800;font-size:.8rem;border-radius:9px;padding:9px 0;cursor:pointer}
.skip{flex:0 0 74px;background:#fff;color:var(--sub);border:1.5px solid var(--line);font-weight:800;font-size:.8rem;border-radius:9px;cursor:pointer}
/* 지도 무대 */
.stage{flex:1 1 auto;position:relative;min-width:0}
svg.map{position:absolute;inset:0;width:100%;height:100%;display:block;background:var(--sea);touch-action:manipulation}
.land{fill:var(--land);stroke:#33534f22;stroke-width:.6;stroke-linejoin:round}
.arc{fill:none;stroke:var(--accent);stroke-width:1.6;stroke-linecap:round;filter:drop-shadow(0 .5px 1px #f2603f33)}
.origin-dot{fill:var(--ink)}.origin-ring{fill:none;stroke:var(--ink);stroke-width:1.5;opacity:.35}
.pin{cursor:pointer}.pin .halo{opacity:.16}.pin .core{stroke:#fff;stroke-width:2.2;transition:r .12s}
.pin.act .core{stroke-width:3;r:9}.pin.act .halo{opacity:.28}
.plabel{font-size:13px;font-weight:800;fill:var(--ink);paint-order:stroke;stroke:var(--sea);stroke-width:3px;pointer-events:none}
.plabel.minor{font-size:11px;font-weight:700;fill:#4a6a66}
.stagebar{position:absolute;left:18px;bottom:18px;display:flex;gap:6px}
.zoom{position:absolute;right:16px;bottom:18px;display:flex;flex-direction:column;background:#fff;border:1px solid var(--line);border-radius:10px;overflow:hidden;box-shadow:0 4px 14px rgba(20,40,40,.12)}
.zoom button{width:38px;height:38px;border:0;background:none;font-size:1.2rem;color:var(--ink);cursor:pointer}.zoom button+button{border-top:1px solid var(--line)}
.prompt{position:absolute;left:18px;top:16px;background:#ffffffdd;border:1px solid var(--line);border-radius:11px;padding:9px 13px;font-size:.74rem;color:var(--sub)}
.prompt b{color:var(--ink);font-weight:800}
/* 지도 위 플로팅 카드(핀/항로 끝) */
.hovercard{position:absolute;width:184px;background:#fff;border-radius:14px;overflow:hidden;box-shadow:0 12px 32px rgba(20,40,40,.26);border:1px solid var(--line);transform:translate(-50%,0) scale(.96);opacity:0;pointer-events:none;transition:opacity .14s ease,transform .14s ease;z-index:6}
.hovercard.show{opacity:1;transform:translate(-50%,0) scale(1)}
.hc-photo{height:92px;position:relative;background-size:cover;background-position:center}
.hc-photo .cityname{position:absolute;left:10px;bottom:7px;color:#fff;font-weight:900;font-size:1.05rem;text-shadow:0 1px 6px #0009;letter-spacing:-.02em}
.hc-photo .ph-tag{position:absolute;right:8px;top:8px;font-size:.54rem;color:#fff9;background:#0004;border-radius:5px;padding:1px 5px}
.hc-body{padding:9px 12px 11px}.hc-row{display:flex;align-items:baseline;justify-content:space-between}
.hc-price{font-weight:900;font-size:1.22rem;color:var(--accent);letter-spacing:-.02em}.hc-price small{font-size:.7rem;font-weight:900}.hc-price .tilde{font-size:.7rem;color:var(--sub);font-weight:700}
.hc-why{font-size:.64rem;color:var(--ink);opacity:.82;margin-top:2px;line-height:1.38}
.hc-tags{display:flex;gap:4px;margin-top:7px}
.hc-cta{margin-top:8px;background:var(--accent);color:#fff;text-align:center;font-weight:800;font-size:.72rem;border-radius:8px;padding:7px 0}
@media(max-width:860px){
  .layout{flex-direction:column}
  .stage{flex:1 1 58%}
  .feed{flex:0 0 42%;order:2;flex-direction:row;overflow-x:auto;overflow-y:hidden;border-right:0;border-top:1px solid var(--line)}
  .feedhead{display:none}
  .fcard{flex:0 0 240px}.fcard.hero{flex-direction:row}.fcard.hero .thumb{width:62px;height:62px;margin:0}
  .gorow{display:none}
}
</style></head><body>
<div class="hdr"><span class="logo">갈래<em>말래</em></span>
  <span class="nav"><span class="on">발견</span><span>오늘의특가</span><span>노선별</span><span>알림</span></span>
  <span class="tools"><span class="pill on">서울 출발 ▾</span><span class="pill">해변</span><span class="pill">도시</span><span class="pill">온천</span></span>
</div>
<div class="layout">
  <div class="feed" id="feed"></div>
  <div class="stage">
    <svg class="map" id="map" preserveAspectRatio="xMidYMid slice">
      <g id="lands"></g><path id="arc" class="arc" d=""/><g id="origin"></g><g id="pins"></g>
    </svg>
    <div class="prompt"><b>카드에 올리면</b> 지도에 항로가 날아가요 · <b>핀에 올리면</b> 카드가 켜져요</div>
    <div class="stagebar"><span class="pill on">가까운 곳</span><span class="pill">＋ 동남아</span><span class="pill">＋ 유럽·미주</span></div>
    <div class="zoom"><button>＋</button><button>－</button></div>
    <div class="hovercard" id="hc"></div>
  </div>
</div>
<script>__D3ARRAY__</script>
<script>__D3GEO__</script>
<script>var WORLD=__WORLD__;</script>
<script>__APP__</script>
</body></html>"""

html=(HTML.replace("__D3ARRAY__",d3arr).replace("__D3GEO__",d3geo)
      .replace("__WORLD__",world).replace("__APP__",APP))
OUT.write_text(html,encoding="utf-8")
print("생성:",OUT,"(",len(html)//1024,"KB )")
