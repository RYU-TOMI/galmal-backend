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
var sortMode='value';   // value(가성비) | imminent(임박) | discount(할인율)
var mood=null;          // 해변 | 도시 | 온천
var dateMode='';        // '' | week | weekend | nextmonth | custom
var dateCustom=null;    // [lo,hi] dkey(MMDD)
var DATE_RANGES={week:[801,807],weekend:[808,810],nextmonth:[901,930]};
var BUDGET_MAX=260000;
var budget=999999;      // 예산 상한(원)
function svgToClient(x,y){var pt=svg.createSVGPoint();pt.x=x;pt.y=y;return pt.matrixTransform(svg.getScreenCTM());}
function dkey(d){var m=d.match(/(\d+)\/(\d+)/);return m?(+m[1])*100+(+m[2]):9999;}
function discNum(s){return parseInt(s,10)||0;}
function dateDim(c){if(!dateMode)return false;var k=dkey(c.date);
  if(dateMode==='custom'){if(!dateCustom)return false;return k<dateCustom[0]||k>dateCustom[1];}
  var r=DATE_RANGES[dateMode];return r?(k<r[0]||k>r[1]):false;}
function dimmed(c){return (mood&&c.tags.indexOf(mood)<0)||(num(c.price)>budget)||dateDim(c);}
function anyFilter(){return mood||dateMode||budget<BUDGET_MAX;}

function visibleCities(){var out=[];
  if(anyFilter()){ // 필터 켜면 거리·등급 무관 전 지역에서 매칭
    CITY.forEach(function(c,i){c._i=i;out.push(c);});
  }else{ // 평소엔 현재 단계 + LOD
    var upto=STAGES.slice(0,stageIdx+1),showMinor=VIEWS[STAGES[stageIdx]].scale>=MINOR_SCALE;
    CITY.forEach(function(c,i){if(upto.indexOf(c.haul)>=0&&(showMinor||c.tier==='major')){c._i=i;out.push(c);}});
  }
  var cmp={value:function(a,b){return num(a.price)-num(b.price);},
           imminent:function(a,b){return dkey(a.date)-dkey(b.date);},
           discount:function(a,b){return discNum(b.disc)-discNum(a.disc);}};
  // 필터에 맞는(안 흐린) 딜을 위로, 그 안에서 정렬 기준 적용
  out.sort(function(a,b){var da=dimmed(a)?1:0,db=dimmed(b)?1:0;if(da!==db)return da-db;return cmp[sortMode](a,b);});
  return out;}

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
    var g=document.createElementNS(SVGNS,'g');g.setAttribute('class','pin'+(dimmed(c)?' dim':''));g.dataset.i=c._i;
    g.innerHTML='<circle class="halo" cx="'+c.x+'" cy="'+c.y+'" r="'+(PIN_R*1.6)+'" fill="'+c._col+'"/>'+
      '<circle class="core" cx="'+c.x+'" cy="'+c.y+'" r="'+PIN_R+'" fill="'+c._col+'"/>'+
      '<text class="plabel'+(c.tier==='minor'?' minor':'')+'" x="'+c.x+'" y="'+(c.y+PIN_R+11)+'" text-anchor="middle">'+c.n+'</text>';
    (function(el,i){el.addEventListener('mouseenter',function(){highlight(i,true);});
      el.addEventListener('click',function(e){e.stopPropagation();expand(i);});})(g,c._i);
    pins.appendChild(g);
  });
  // 카드 피드
  feed.innerHTML='<div class="feedhead"><div class="fh-top"><b>오늘의 발견</b><span>'+(anyFilter()?'전 지역에서 찾는 중':'서울 출발 · '+vis.length+'곳')+'</span></div>'+
    '<div class="sortbar">'+
     '<button class="spill'+(sortMode==='value'?' on':'')+'" data-sort="value">가성비순</button>'+
     '<button class="spill'+(sortMode==='imminent'?' on':'')+'" data-sort="imminent">임박순</button>'+
     '<button class="spill'+(sortMode==='discount'?' on':'')+'" data-sort="discount">할인율순</button>'+
    '</div></div>';
  var matches=[];for(var q=0;q<vis.length;q++)if(!dimmed(vis[q]))matches.push(vis[q]);
  if(anyFilter()&&matches.length===0){var nt=document.createElement('div');nt.className='feednote';
    nt.textContent='이 조건엔 딜이 없어요 — 조건을 바꿔보세요';feed.appendChild(nt);}
  // hero = 매칭 중 할인율 최고(동률이면 임박) — "진짜 갈래말래?"
  var heroCity=null;
  matches.forEach(function(c){if(!heroCity||discNum(c.disc)>discNum(heroCity.disc)||(discNum(c.disc)===discNum(heroCity.disc)&&dkey(c.date)<dkey(heroCity.date)))heroCity=c;});
  var order=heroCity?[heroCity].concat(vis.filter(function(c){return c!==heroCity;})):vis;
  order.forEach(function(c){
    var hero=(c===heroCity);
    var card=document.createElement('div');card.className='fcard'+(hero?' hero':'')+(dimmed(c)?' dim':'');card.dataset.i=c._i;
    card.innerHTML=
      '<div class="thumb" style="background:'+c.g+'">'+(hero?'<span class="pick">진짜 갈래말래?</span>':'')+'</div>'+
      '<div class="fbody"><div class="frow"><b class="fcity">'+c.n+'</b><span class="stamp">'+c.disc+'</span></div>'+
      '<div class="fprice"><small>₩</small>'+c.price+' <span class="tilde">~</span></div>'+
      '<div class="fdate"><span class="when">'+c.when+'</span>'+c.date+' · '+c.nights+'</div>'+
      '<div class="fwhy">'+c.why+'</div>'+
      '<div class="ftags">'+c.tags.map(function(t){return '<span class="tag">'+t+'</span>';}).join('')+'</div>'+
      (hero?'<div class="gorow"><button class="go">갈래 → 자세히 보기</button></div>':'')+
      '</div>';
    (function(el,i){el.addEventListener('mouseenter',function(){highlight(i,false);});
      el.addEventListener('click',function(){expand(i);});})(card,c._i);
    feed.appendChild(card);
  });
  var sps=feed.querySelectorAll('.spill');
  for(var s=0;s<sps.length;s++){(function(el){el.addEventListener('click',function(){sortMode=el.dataset.sort;collapse();render();});})(sps[s]);}
  if(active!==null)paintActive();
}

function cityByI(i){for(var k=0;k<CITY.length;k++)if(CITY[k]._i===i&&CITY[k].x!=null)return CITY[k];
  return CITY[i];}
function paintActive(){
  var ps=document.querySelectorAll('.pin');for(var k=0;k<ps.length;k++)ps[k].classList.toggle('act',+ps[k].dataset.i===active);
  var cs=document.querySelectorAll('.fcard');for(var j=0;j<cs.length;j++)cs[j].classList.toggle('on',+cs[j].dataset.i===active);
}
var expandedI=null;
function drawArc(c){var mx=(ORIGIN.x+c.x)/2,my=(ORIGIN.y+c.y)/2,dx=c.x-ORIGIN.x,dy=c.y-ORIGIN.y,len=Math.hypot(dx,dy)||1;
  var lift=Math.min(90,len*0.24),cx=mx-dy/len*lift,cy=my+dx/len*lift;
  arc.setAttribute('d','M'+ORIGIN.x+','+ORIGIN.y+' Q'+cx+','+cy+' '+c.x+','+c.y);
  var L=arc.getTotalLength();arc.style.transition='none';arc.style.strokeDasharray=L;arc.style.strokeDashoffset=L;
  arc.getBoundingClientRect();arc.style.transition='stroke-dashoffset .42s ease';arc.style.strokeDashoffset=0;}
function photoHTML(c){return '<div class="hc-photo" style="background:'+c.g+'"><span class="ph-tag">사진 · Unsplash</span><span class="cityname">'+c.n+'</span></div>';}
function bodyTop(c){return '<div class="hc-row"><span class="hc-price"><small>₩</small>'+c.price+' <span class="tilde">~</span></span><span class="stamp">특가 '+c.disc+'</span></div>'+
  '<div class="hc-date">'+c.date+' · '+c.nights+'</div>'+
  '<div class="hc-why">'+c.why+'</div>'+
  '<div class="hc-tags">'+c.tags.map(function(t){return '<span class="tag">'+t+'</span>';}).join('')+'</div>';}
function spark(){var pts=[28,25,30,22,26,19,24,16,20,15],Ws=152,Hs=38,st=Ws/(pts.length-1),mi=pts.indexOf(Math.min.apply(null,pts));
  var co=pts.map(function(v,i){return [Math.round(i*st),Math.round(Hs-(v/32*Hs))];});
  return '<svg class="spark" viewBox="0 0 '+Ws+' '+Hs+'"><path d="M'+co.map(function(p){return p[0]+','+p[1];}).join(' L')+'" fill="none" stroke="var(--coast)" stroke-width="2"/><circle cx="'+co[mi][0]+'" cy="'+co[mi][1]+'" r="3.5" fill="var(--accent)"/></svg>';}
function compactHTML(c){return photoHTML(c)+'<div class="hc-body">'+bodyTop(c)+'<div class="hc-cta">갈래 → 자세히 보기</div></div>';}
function detailHTML(c){return photoHTML(c)+'<div class="hc-body">'+bodyTop(c)+
  '<div class="hc-detail"><div class="hc-sec">최근 30일 가격</div>'+spark()+
   '<div class="hc-sec">직항 · 약 5시간 · 최저가 기준일</div>'+
   '<a class="hc-cta big">갈래 → 예약하러 가기</a>'+
   '<div class="hc-ad">예약이 이뤄지면 수수료를 받을 수 있어요 · (광고)</div>'+
  '</div></div>';}
function positionCard(c){var cp=svgToClient(c.x,c.y),box=stageEl.getBoundingClientRect(),h=hc.offsetHeight;
  var left=cp.x-box.left,top=cp.y-box.top-16-h;if(top<8)top=cp.y-box.top+20;
  left=Math.max(120,Math.min(box.width-120,left));hc.style.left=left+'px';hc.style.top=top+'px';}
function showCard(i,scroll,expanded){
  active=i;var c=cityByI(i);paintActive();
  if(!c||c.x==null){hc.classList.remove('show');return;}
  drawArc(c);
  hc.classList.toggle('expanded',!!expanded);
  hc.innerHTML=expanded?detailHTML(c):compactHTML(c);
  hc.classList.add('show');positionCard(c);
  if(scroll){var card=document.querySelector('.fcard[data-i="'+i+'"]');if(card)card.scrollIntoView({behavior:'smooth',block:'nearest',inline:'nearest'});}
}
function highlight(i,scroll){if(expandedI!==null)return;showCard(i,scroll,false);}
function expand(i){expandedI=i;showCard(i,true,true);}
function clearHi(){if(expandedI!==null)return;active=null;paintActive();hc.classList.remove('show');
  if(arc.getTotalLength){arc.style.transition='stroke-dashoffset .2s ease';arc.style.strokeDashoffset=arc.getTotalLength();}}
function collapse(){expandedI=null;active=null;paintActive();hc.classList.remove('show','expanded');
  if(arc.getTotalLength){arc.style.transition='stroke-dashoffset .2s ease';arc.style.strokeDashoffset=arc.getTotalLength();}}
hc.addEventListener('click',function(e){e.stopPropagation();});

function setStage(idx){stageIdx=idx;collapse();render();
  var bs=document.querySelectorAll('.stagebar .pill');for(var k=0;k<bs.length;k++)bs[k].classList.toggle('on',k===idx);}
var bs=document.querySelectorAll('.stagebar .pill');
for(var b=0;b<bs.length;b++){(function(el,idx){el.addEventListener('click',function(){setStage(idx);});})(bs[b],b);}
stageEl.addEventListener('mouseleave',function(){if(matchMedia('(hover:hover)').matches)clearHi();});
svg.addEventListener('click',function(e){if(e.target===svg||e.target.classList.contains('land'))collapse();});

// 오른쪽 아래 필터 도크
var bslider=document.getElementById('budget'),bval=document.getElementById('budgetVal');
budget=+bslider.value;
function updCount(){var n=0;
  if(dateMode&&!(dateMode==='custom'&&!dateCustom))n++;
  if(mood)n++;if(budget<BUDGET_MAX)n++;
  document.getElementById('fdcount').textContent=n?('· '+n):'';}
// 날짜(단일 선택 + 달력 지정)
var dateEls=document.querySelectorAll('.fchip.date');
var customBox=document.getElementById('customdates');
function setActiveDate(mode){dateMode=mode;
  for(var k=0;k<dateEls.length;k++)dateEls[k].classList.toggle('on',dateEls[k].dataset.date===mode);
  customBox.classList.toggle('show',mode==='custom');}
for(var di=0;di<dateEls.length;di++){(function(el){el.addEventListener('click',function(){
  setActiveDate(el.dataset.date);
  if(dateMode!=='custom')dateCustom=null;
  updCount();collapse();render();});})(dateEls[di]);}
function readCustom(){function k(v){if(!v)return null;var p=v.split('-');return (+p[1])*100+(+p[2]);}
  var lo=k(document.getElementById('cdStart').value),hi=k(document.getElementById('cdEnd').value);
  dateCustom=(lo===null&&hi===null)?null:[lo===null?0:lo,hi===null?9999:hi];}
['cdStart','cdEnd'].forEach(function(id){document.getElementById(id).addEventListener('change',function(){
  setActiveDate('custom');readCustom();updCount();collapse();render();});});
// 분위기(토글)
var moodEls=document.querySelectorAll('.fchip.moodf');
for(var mi=0;mi<moodEls.length;mi++){(function(el){el.addEventListener('click',function(){
  var m=el.dataset.mood;mood=(mood===m?null:m);
  for(var k=0;k<moodEls.length;k++)moodEls[k].classList.toggle('on',moodEls[k].dataset.mood===mood);
  updCount();collapse();render();});})(moodEls[mi]);}
// 예산 슬라이더(실시간)
bslider.addEventListener('input',function(){budget=+bslider.value;bval.textContent=Math.round(budget/10000)+'만';updCount();collapse();render();});
// 접기/펼치기
var fdock=document.getElementById('fdock');
document.getElementById('fdtoggle').addEventListener('click',function(){fdock.classList.toggle('collapsed');});
updCount();

// 화면0: 출발지 5핀
var AIRPORTS=[{n:'서울',lon:126.99,lat:37.55},{n:'청주',lon:127.50,lat:36.72},{n:'대구',lon:128.66,lat:35.90},{n:'부산',lon:129.03,lat:35.18},{n:'제주',lon:126.49,lat:33.51}];
function renderIntro(){
  var im=document.getElementById('introMap');
  var ip=d3.geoEquirectangular().rotate([-127.7,0]).center([0,35.9]).scale(3100).translate([200,150]);
  var ipath=d3.geoPath(ip);
  var lp2=document.createElementNS(SVGNS,'path');lp2.setAttribute('d',ipath(WORLD));lp2.setAttribute('class','land');im.appendChild(lp2);
  AIRPORTS.forEach(function(a){var p=ip([a.lon,a.lat]);
    var g=document.createElementNS(SVGNS,'g');g.setAttribute('class','ap');
    g.innerHTML='<circle class="aph" cx="'+p[0]+'" cy="'+p[1]+'" r="14"/>'+
      '<circle class="apr" cx="'+p[0]+'" cy="'+p[1]+'" r="7"/>'+
      '<text class="aplabel" x="'+p[0]+'" y="'+(p[1]-13)+'" text-anchor="middle">'+a.n+'</text>';
    g.addEventListener('click',function(){pickOrigin(a.n);});
    im.appendChild(g);});
}
function pickOrigin(name){document.getElementById('originPill').textContent=name+' 출발 ▾';
  document.getElementById('intro').classList.add('hide');}
document.getElementById('originPill').addEventListener('click',function(){document.getElementById('intro').classList.remove('hide');});
renderIntro();
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
.gm-logo{position:relative;display:inline-block;font-weight:900;letter-spacing:-.03em;color:var(--ink);line-height:1;font-size:1.3rem;margin-right:16px}
.gm-logo em{font-style:normal;color:var(--accent)}
.gm-logo .lg{position:absolute;left:46%;right:0;bottom:-24%;height:1.1em;overflow:visible}
.gm-logo .pl-top{fill:var(--accent)}.gm-logo .pl-btm{fill:var(--accent2)}
.gm-logo .pl-crease{stroke:#ffffff88;stroke-width:.8;fill:none}
.nav{display:flex;gap:4px;margin-left:26px;font-size:.85rem;color:var(--sub);font-weight:600}.nav .on{color:var(--ink);font-weight:800}
.tools{margin-left:auto;display:flex;gap:7px}
.pill{border:1.5px solid var(--line);border-radius:99px;padding:6px 12px;font-size:.78rem;color:var(--sub);background:#fff;font-weight:700;cursor:pointer}
.pill.on{background:var(--accent);color:#fff;border-color:var(--accent)}
.layout{flex:1 1 auto;display:flex;min-height:0;position:relative}
.mood.pill{cursor:pointer}.mood.pill.on{background:var(--accent);color:#fff;border-color:var(--accent)}
.budget{display:flex;align-items:center;gap:7px;font-size:.74rem;font-weight:700;color:var(--sub);margin-left:4px}
.budget input[type=range]{width:104px;accent-color:var(--accent);cursor:pointer}
.budget b{color:var(--ink)}
/* 카드 피드 레일 */
.feed{flex:0 0 340px;overflow-y:auto;padding:14px;background:var(--bg);border-right:1px solid var(--line);display:flex;flex-direction:column;gap:10px}
.feedhead{padding:2px 2px 2px}
.fh-top{display:flex;justify-content:space-between;align-items:baseline}
.feedhead b{font-size:1.05rem;font-weight:900;letter-spacing:-.02em}.feedhead span{font-size:.7rem;color:var(--sub)}
.sortbar{display:flex;gap:5px;margin-top:8px}
.spill{font-size:.68rem;font-weight:700;padding:5px 10px;border-radius:99px;border:1px solid var(--line);background:#fff;color:var(--sub);cursor:pointer}
.spill.on{background:var(--ink);color:#fff;border-color:var(--ink)}
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
.zoom{position:absolute;right:16px;top:16px;display:flex;flex-direction:column;background:#fff;border:1px solid var(--line);border-radius:10px;overflow:hidden;box-shadow:0 4px 14px rgba(20,40,40,.12)}
.zoom button{width:38px;height:38px;border:0;background:none;font-size:1.2rem;color:var(--ink);cursor:pointer}.zoom button+button{border-top:1px solid var(--line)}
/* 오른쪽 아래 필터 도크 */
.filterdock{position:absolute;right:16px;bottom:18px;width:270px;background:#fff;border:1px solid var(--line);border-radius:14px;box-shadow:0 10px 30px rgba(20,40,40,.18);overflow:hidden;z-index:7}
.fdtoggle{width:100%;display:flex;align-items:center;justify-content:space-between;border:0;background:#fff;font-weight:800;font-size:.9rem;color:var(--ink);padding:12px 15px;cursor:pointer}
.fdtoggle #fdcount{color:var(--accent);font-size:.76rem;margin-left:auto;margin-right:8px}
.fdtoggle i{font-style:normal;color:var(--sub);transition:transform .2s}
.filterdock.collapsed .fdbody{display:none}
.filterdock.collapsed .fdtoggle i{transform:rotate(-90deg)}
.fdbody{padding:2px 15px 15px;display:flex;flex-direction:column;gap:12px;border-top:1px solid var(--line)}
.fdrow{display:flex;flex-direction:column;gap:7px}
.fdlabel{font-size:.7rem;font-weight:800;color:var(--sub)}
.chips{display:flex;gap:6px;flex-wrap:wrap}
.fchip{font-size:.74rem;font-weight:700;padding:6px 11px;border-radius:99px;border:1px solid var(--line);background:#fff;color:var(--sub);cursor:pointer}
.fchip.on{background:var(--accent);color:#fff;border-color:var(--accent)}
.budgetwrap{display:flex;align-items:center;gap:8px;font-size:.78rem;font-weight:700;color:var(--sub)}
.budgetwrap input{flex:1;accent-color:var(--accent);cursor:pointer}.budgetwrap b{color:var(--ink)}
.customdates{display:none;gap:6px;align-items:center;margin-top:8px;font-size:.72rem;color:var(--sub)}
.customdates.show{display:flex}
.customdates input{border:1px solid var(--line);border-radius:8px;padding:5px 7px;font:inherit;font-size:.72rem;color:var(--ink);accent-color:var(--accent)}
.feednote{background:var(--soft);border:1px dashed var(--line2,#cfd8d7);border-radius:10px;padding:11px 12px;font-size:.76rem;color:var(--sub);font-weight:600;text-align:center}
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
.hc-date{font-size:.66rem;color:var(--sub);font-weight:700;margin-top:3px}
/* 확장(클릭) 상세 카드 */
.hovercard.expanded{width:238px;pointer-events:auto}
.hc-detail{margin-top:9px;border-top:1px dashed var(--line);padding-top:9px}
.hc-sec{font-size:.63rem;font-weight:800;color:var(--sub);margin:2px 0 6px}
.spark{width:100%;height:38px;display:block;margin-bottom:8px}
.hc-cta.big{display:block;margin-top:10px}
.hc-ad{font-size:.56rem;color:var(--sub);opacity:.85;margin-top:6px;text-align:center}
/* 필터 흐림(dim) */
.pin.dim{opacity:.28}.pin.dim .core{stroke-width:1.4}
.fcard.dim{opacity:.42;filter:saturate(.55)}
/* 화면0 출발지 선택 */
.intro{position:absolute;inset:0;z-index:20;background:var(--bg);display:flex;flex-direction:column;align-items:center;justify-content:center;gap:8px;transition:opacity .5s ease}
.intro.hide{opacity:0;pointer-events:none}
.intro h2{font-size:1.95rem;font-weight:900;letter-spacing:-.03em}
.intro p{color:var(--sub);font-size:.9rem}
.krwrap{width:min(560px,84vw);margin-top:6px}
#introMap{width:100%;height:auto;aspect-ratio:4/3;background:var(--sea);border:1px solid var(--line);border-radius:18px;box-shadow:inset 0 1px 8px rgba(0,0,0,.05)}
#introMap .land{fill:var(--land);stroke:#33534f22;stroke-width:.5}
#introMap .ap{cursor:pointer}
#introMap .ap .apr{fill:var(--accent);stroke:#fff;stroke-width:2;transition:r .12s}
#introMap .ap:hover .apr{r:11}
#introMap .ap .aph{fill:var(--accent);opacity:.16}
#introMap .aplabel{font-size:12px;font-weight:800;fill:var(--ink);paint-order:stroke;stroke:var(--sea);stroke-width:3px;pointer-events:none}
@media(max-width:860px){
  .layout{flex-direction:column}
  .stage{flex:1 1 58%}
  .feed{flex:0 0 42%;order:2;flex-direction:row;overflow-x:auto;overflow-y:hidden;border-right:0;border-top:1px solid var(--line)}
  .feedhead{display:none}
  .fcard{flex:0 0 240px}.fcard.hero{flex-direction:row}.fcard.hero .thumb{width:62px;height:62px;margin:0}
  .gorow{display:none}
}
</style></head><body>
<div class="hdr"><span class="gm-logo">갈래<em>말래</em><svg class="lg" viewBox="0 0 170 46" overflow="visible" aria-hidden="true"><defs><linearGradient id="gmlg" x1="0" x2="1"><stop offset="0" stop-color="#F2603F" stop-opacity="0"/><stop offset="1" stop-color="#F2603F" stop-opacity=".95"/></linearGradient></defs><path d="M6,34 Q76,40 114,19" fill="none" stroke="url(#gmlg)" stroke-width="3" stroke-linecap="round"/><g transform="translate(120,16) rotate(-28.6) scale(1.02)"><path class="pl-btm" d="M13,0 L-4,0 L-11,8 Z"/><path class="pl-top" d="M13,0 L-11,-8 L-4,0 Z"/><path class="pl-crease" d="M13,0 L-4,0"/></g></svg></span>
  <span class="nav"><span class="on">발견</span><span>노선별</span></span>
  <span class="tools"><span class="pill origin" id="originPill">서울 출발 ▾</span></span>
</div>
<div class="layout">
  <div class="intro" id="intro">
    <h2>어디서 출발하세요?</h2>
    <p>출발 공항을 고르면 오늘 싼 곳들이 열려요</p>
    <div class="krwrap"><svg id="introMap" viewBox="0 0 400 300" preserveAspectRatio="xMidYMid meet"></svg></div>
  </div>
  <div class="feed" id="feed"></div>
  <div class="stage">
    <svg class="map" id="map" preserveAspectRatio="xMidYMid slice">
      <g id="lands"></g><path id="arc" class="arc" d=""/><g id="origin"></g><g id="pins"></g>
    </svg>
    <div class="prompt"><b>카드에 올리면</b> 지도에 항로가 날아가요 · <b>핀에 올리면</b> 카드가 켜져요</div>
    <div class="stagebar"><span class="pill on">가까운 곳</span><span class="pill">＋ 동남아</span><span class="pill">＋ 유럽·미주</span></div>
    <div class="zoom"><button>＋</button><button>－</button></div>
    <div class="filterdock" id="fdock">
      <button class="fdtoggle" id="fdtoggle">필터 <span id="fdcount"></span><i>▾</i></button>
      <div class="fdbody">
        <div class="fdrow"><span class="fdlabel">언제 갈래요?</span>
          <div class="chips">
            <button class="fchip date on" data-date="">아무때</button>
            <button class="fchip date" data-date="week">이번 주</button>
            <button class="fchip date" data-date="weekend">이번 주말</button>
            <button class="fchip date" data-date="nextmonth">다음 달</button>
            <button class="fchip date" data-date="custom">날짜 지정</button>
          </div>
          <div class="customdates" id="customdates">
            <input type="date" id="cdStart"><span>~</span><input type="date" id="cdEnd">
          </div></div>
        <div class="fdrow"><span class="fdlabel">분위기</span>
          <div class="chips">
            <button class="fchip moodf" data-mood="해변">해변</button>
            <button class="fchip moodf" data-mood="도시">도시</button>
            <button class="fchip moodf" data-mood="온천">온천</button>
          </div></div>
        <div class="fdrow"><span class="fdlabel">예산</span>
          <div class="budgetwrap"><input id="budget" type="range" min="110000" max="260000" step="5000" value="260000"><b id="budgetVal">26만</b> 이하</div></div>
      </div>
    </div>
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
