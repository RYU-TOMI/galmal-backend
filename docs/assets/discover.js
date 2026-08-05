/* 갈래말래 발견 홈 — 지도(무대) + '오늘의 발견' 카드 피드 + 필터 도크 + 확장 상세.
   데이터는 window.__DEALS(deals.json), 지도 윤곽은 window.__WORLD(geojson). d3-geo만 사용. */
(function () {
  "use strict";
  var D = window.__DEALS, WORLD = window.__WORLD;
  var svg = document.getElementById("map");
  if (!D || !WORLD || !svg || !window.d3 || !d3.geoEquirectangular) return;

  var SVGNS = "http://www.w3.org/2000/svg";
  var W = 1000, H = 680, MINOR_SCALE = 1200;
  var VIEWS = { near: { lon: 132, lat: 35.5, scale: 1500 },
                sea: { lon: 117, lat: 19, scale: 720 },
                far: { lon: 78, lat: 30, scale: 230 } };
  var STAGES = ["near", "sea", "far"];
  var HAUL2STAGE = { short: "near", mid: "sea", long: "far" };
  var WD = ["일", "월", "화", "수", "목", "금", "토"];
  var TAG_GRAD = {
    "해변": "linear-gradient(135deg,#8fd0e0,#2a6f8f)", "온천": "linear-gradient(135deg,#ffc07a,#e0782f)",
    "도시": "linear-gradient(135deg,#ff9a76,#c6472a)", "미식": "linear-gradient(135deg,#f2603f,#7a2e18)",
    "자연": "linear-gradient(135deg,#a8e0c0,#2a8f6c)", "설경": "linear-gradient(135deg,#cfe6ff,#5a7fa0)",
    "야시장": "linear-gradient(135deg,#ffb08a,#c6472a)", "쇼핑": "linear-gradient(135deg,#ffb89a,#c6502a)",
    "문화": "linear-gradient(135deg,#ffcf9a,#c6652a)", "휴양": "linear-gradient(135deg,#8fe0d0,#2a8f7c)",
    "유적": "linear-gradient(135deg,#ffcf9a,#c6652a)", "액티비티": "linear-gradient(135deg,#9fe0c0,#2a8f6c)",
    "야경": "linear-gradient(135deg,#f2603f,#7a2e18)", "트레킹": "linear-gradient(135deg,#a8e0c0,#2a8f6c)"
  };

  // ---- 딜 → 카드 표시 필드 변환 ----
  function fmtMD(iso) { var p = iso.split("-"), dt = new Date(+p[0], +p[1] - 1, +p[2]); return (+p[1]) + "/" + (+p[2]) + "(" + WD[dt.getDay()] + ")"; }
  function fmtRange(dep, ret) { return ret ? fmtMD(dep) + "~" + fmtMD(ret) : fmtMD(dep); }
  function grad(tags) { for (var i = 0; i < tags.length; i++) if (TAG_GRAD[tags[i]]) return TAG_GRAD[tags[i]]; return "linear-gradient(135deg,#ffb89a,#c6502a)"; }
  function whyOf(dl) {
    if (dl.discount >= 25) return "평소보다 " + dl.discount + "%↓";
    if (dl.transfers > 0) return "경유로 확 싸진 특가";
    if (dl.when === "이번 주말") return "이번 주말 바로 출발";
    if (dl.discount > 0) return "최근 " + dl.discount + "%↓ · " + dl.when;
    return dl.when + " 최저가";
  }
  function toCity(dl) {
    return { n: dl.ko, lon: dl.lon, lat: dl.lat, tier: dl.tier, haul: HAUL2STAGE[dl.haul] || "far",
      price: (dl.price).toLocaleString("en-US"), disc: (dl.discount || 0) + "%↓",
      when: dl.when, date: fmtRange(dl.dep, dl.ret), nights: dl.nights || "", dep: dl.dep,
      why: whyOf(dl), tags: dl.tags, g: grad(dl.tags), country: dl.country, links: dl.links || [] };
  }

  // ---- 파싱/공용 ----
  var LIGHT = [247, 178, 158], DEEP = [214, 60, 30];
  function lerp(a, b, t) { return Math.round(a + (b - a) * t); }
  function num(p) { return +p.replace(/[^0-9]/g, ""); }
  function dkey(d) { var m = d.match(/(\d+)\/(\d+)/); return m ? (+m[1]) * 100 + (+m[2]) : 9999; }
  function discNum(s) { return parseInt(s, 10) || 0; }

  svg.setAttribute("viewBox", "0 0 " + W + " " + H);
  var proj = d3.geoEquirectangular().translate([W / 2, H / 2]);
  var path = d3.geoPath(proj);
  var landPath = document.createElementNS(SVGNS, "path"); landPath.setAttribute("class", "land");
  document.getElementById("lands").appendChild(landPath);
  var arc = document.getElementById("arc"), pins = document.getElementById("pins"), og = document.getElementById("origin");
  var feed = document.getElementById("feed"), stageEl = document.querySelector(".stage"), hc = document.getElementById("hc");
  var bslider = document.getElementById("budget"), bval = document.getElementById("budgetVal");
  var BUDGET_MAX = bslider ? +bslider.max : 1000000;

  var ORIGIN = null, CITY = [], stageIdx = 0, active = null, expandedI = null;
  var sortMode = "value", mood = null, dateMode = "", dateCustom = null, budget = 1e12;

  function isoOf(dt) { return dt.getFullYear() + "-" + String(dt.getMonth() + 1).padStart(2, "0") + "-" + String(dt.getDate()).padStart(2, "0"); }
  function dateWindow() {
    var t = new Date(); t.setHours(0, 0, 0, 0);
    if (dateMode === "week") { var e = new Date(t); e.setDate(e.getDate() + 7); return [isoOf(t), isoOf(e)]; }
    if (dateMode === "weekend") { var d = t.getDay(), toFri = (5 - d + 7) % 7; var fri = new Date(t); fri.setDate(fri.getDate() + toFri); var sun = new Date(fri); sun.setDate(sun.getDate() + 2); return [isoOf(fri), isoOf(sun)]; }
    if (dateMode === "nextmonth") { var y = t.getFullYear(), m = t.getMonth() + 1; return [isoOf(new Date(y, m, 1)), isoOf(new Date(y, m + 1, 0))]; }
    if (dateMode === "custom") return dateCustom;
    return null;
  }
  function dateDim(c) { var w = dateWindow(); if (!w) return false; return c.dep < w[0] || c.dep > w[1]; }
  function dimmed(c) { return (mood && c.tags.indexOf(mood) < 0) || (num(c.price) > budget) || dateDim(c); }
  function anyFilter() { return mood || dateMode || budget < BUDGET_MAX; }

  function visibleCities() {
    var out = [];
    if (anyFilter()) {
      CITY.forEach(function (c, i) { c._i = i; out.push(c); });
    } else {
      var upto = STAGES.slice(0, stageIdx + 1), showMinor = VIEWS[STAGES[stageIdx]].scale >= MINOR_SCALE;
      CITY.forEach(function (c, i) { if (upto.indexOf(c.haul) >= 0 && (showMinor || c.tier === "major")) { c._i = i; out.push(c); } });
    }
    var cmp = { value: function (a, b) { return num(a.price) - num(b.price); },
                imminent: function (a, b) { return dkey(a.date) - dkey(b.date); },
                discount: function (a, b) { return discNum(b.disc) - discNum(a.disc); } };
    out.sort(function (a, b) { var da = dimmed(a) ? 1 : 0, db = dimmed(b) ? 1 : 0; if (da !== db) return da - db; return cmp[sortMode](a, b); });
    return out;
  }
  function colorMaker(vis) {
    var vn = vis.map(function (c) { return num(c.price); }), lo = Math.min.apply(null, vn), hi = Math.max.apply(null, vn);
    return function (p) { var t = 1 - (num(p) - lo) / ((hi - lo) || 1);
      return "rgb(" + lerp(LIGHT[0], DEEP[0], t) + "," + lerp(LIGHT[1], DEEP[1], t) + "," + lerp(LIGHT[2], DEEP[2], t) + ")"; };
  }

  var PIN_R = 6;
  function render() {
    if (!ORIGIN) return;
    var v = VIEWS[STAGES[stageIdx]];
    proj.rotate([-v.lon, 0]).center([0, v.lat]).scale(v.scale).translate([W / 2, H / 2]);
    landPath.setAttribute("d", path(WORLD));
    var O = proj([ORIGIN.lon, ORIGIN.lat]); ORIGIN.x = O[0]; ORIGIN.y = O[1];
    og.innerHTML = '<circle class="origin-ring" cx="' + O[0] + '" cy="' + O[1] + '" r="9"/>' +
      '<circle class="origin-dot" cx="' + O[0] + '" cy="' + O[1] + '" r="4"/>' +
      '<text class="plabel org" x="' + O[0] + '" y="' + (O[1] - 13) + '" text-anchor="middle">' + ORIGIN.n + " 출발</text>";
    var vis = visibleCities(), colorOf = colorMaker(vis);
    vis.forEach(function (c) { var p = proj([c.lon, c.lat]); c.x = p[0]; c.y = p[1]; c._col = colorOf(c.price); });
    pins.innerHTML = "";
    vis.forEach(function (c) {
      var g = document.createElementNS(SVGNS, "g"); g.setAttribute("class", "pin" + (dimmed(c) ? " dim" : "")); g.dataset.i = c._i;
      g.innerHTML = '<circle class="halo" cx="' + c.x + '" cy="' + c.y + '" r="' + (PIN_R * 1.6) + '" fill="' + c._col + '"/>' +
        '<circle class="core" cx="' + c.x + '" cy="' + c.y + '" r="' + PIN_R + '" fill="' + c._col + '"/>' +
        '<text class="plabel' + (c.tier === "minor" ? " minor" : "") + '" x="' + c.x + '" y="' + (c.y + PIN_R + 11) + '" text-anchor="middle">' + c.n + "</text>";
      (function (el, i) { el.addEventListener("mouseenter", function () { highlight(i, true); });
        el.addEventListener("click", function (e) { e.stopPropagation(); expand(i); }); })(g, c._i);
      pins.appendChild(g);
    });
    // 카드 피드
    feed.innerHTML = '<div class="feedhead"><div class="fh-top"><b>오늘의 발견</b><span>' +
      (anyFilter() ? "전 지역에서 찾는 중" : ORIGIN.n + " 출발 · " + vis.length + "곳") + "</span></div>" +
      '<div class="sortbar">' +
      '<button class="spill' + (sortMode === "value" ? " on" : "") + '" data-sort="value">가성비순</button>' +
      '<button class="spill' + (sortMode === "imminent" ? " on" : "") + '" data-sort="imminent">임박순</button>' +
      '<button class="spill' + (sortMode === "discount" ? " on" : "") + '" data-sort="discount">할인율순</button>' +
      "</div></div>";
    var matches = vis.filter(function (c) { return !dimmed(c); });
    if (anyFilter() && matches.length === 0) { var nt = document.createElement("div"); nt.className = "feednote"; nt.textContent = "이 조건엔 딜이 없어요 — 조건을 바꿔보세요"; feed.appendChild(nt); }
    var heroCity = null;
    matches.forEach(function (c) { if (!heroCity || discNum(c.disc) > discNum(heroCity.disc) || (discNum(c.disc) === discNum(heroCity.disc) && dkey(c.date) < dkey(heroCity.date))) heroCity = c; });
    var order = heroCity ? [heroCity].concat(vis.filter(function (c) { return c !== heroCity; })) : vis;
    order.forEach(function (c) {
      var hero = (c === heroCity);
      var card = document.createElement("div"); card.className = "fcard" + (hero ? " hero" : "") + (dimmed(c) ? " dim" : ""); card.dataset.i = c._i;
      card.innerHTML =
        '<div class="thumb" style="background:' + c.g + '">' + (hero ? '<span class="pick">진짜 갈래말래?</span>' : "") + "</div>" +
        '<div class="fbody"><div class="frow"><b class="fcity">' + c.n + '</b><span class="stamp">' + c.disc + "</span></div>" +
        '<div class="fprice"><small>₩</small>' + c.price + ' <span class="tilde">~</span></div>' +
        '<div class="fdate"><span class="when">' + c.when + "</span>" + c.date + (c.nights ? " · " + c.nights : "") + "</div>" +
        '<div class="fwhy">' + c.why + "</div>" +
        '<div class="ftags">' + c.tags.map(function (t) { return '<span class="tag">' + t + "</span>"; }).join("") + "</div>" +
        (hero ? '<div class="gorow"><button class="go">갈래 → 자세히 보기</button></div>' : "") +
        "</div>";
      (function (el, i) { el.addEventListener("mouseenter", function () { highlight(i, false); });
        el.addEventListener("click", function () { expand(i); }); })(card, c._i);
      feed.appendChild(card);
    });
    var sps = feed.querySelectorAll(".spill");
    for (var s = 0; s < sps.length; s++) (function (el) { el.addEventListener("click", function () { sortMode = el.dataset.sort; collapse(); render(); }); })(sps[s]);
    if (active !== null) paintActive();
  }

  // ---- 항로 + 플로팅/확장 카드 ----
  function cityByI(i) { for (var k = 0; k < CITY.length; k++) if (CITY[k]._i === i && CITY[k].x != null) return CITY[k]; return CITY[i]; }
  function paintActive() {
    var ps = document.querySelectorAll(".pin"); for (var k = 0; k < ps.length; k++) ps[k].classList.toggle("act", +ps[k].dataset.i === active);
    var cs = document.querySelectorAll(".fcard"); for (var j = 0; j < cs.length; j++) cs[j].classList.toggle("on", +cs[j].dataset.i === active);
  }
  function drawArc(c) {
    var mx = (ORIGIN.x + c.x) / 2, my = (ORIGIN.y + c.y) / 2, dx = c.x - ORIGIN.x, dy = c.y - ORIGIN.y, len = Math.hypot(dx, dy) || 1;
    var lift = Math.min(90, len * 0.24), cx = mx - dy / len * lift, cy = my + dx / len * lift;
    arc.setAttribute("d", "M" + ORIGIN.x + "," + ORIGIN.y + " Q" + cx + "," + cy + " " + c.x + "," + c.y);
    var L = arc.getTotalLength(); arc.style.transition = "none"; arc.style.strokeDasharray = L; arc.style.strokeDashoffset = L;
    arc.getBoundingClientRect(); arc.style.transition = "stroke-dashoffset .42s ease"; arc.style.strokeDashoffset = 0;
  }
  function svgToClient(x, y) { var pt = svg.createSVGPoint(); pt.x = x; pt.y = y; return pt.matrixTransform(svg.getScreenCTM()); }
  function photoHTML(c) { return '<div class="hc-photo" style="background:' + c.g + '"><span class="ph-tag">사진 준비중</span><span class="cityname">' + c.n + "</span></div>"; }
  function bodyTop(c) {
    return '<div class="hc-row"><span class="hc-price"><small>₩</small>' + c.price + ' <span class="tilde">~</span></span><span class="stamp">특가 ' + c.disc + "</span></div>" +
      '<div class="hc-date">' + c.date + (c.nights ? " · " + c.nights : "") + "</div>" +
      '<div class="hc-why">' + c.why + "</div>" +
      '<div class="hc-tags">' + c.tags.map(function (t) { return '<span class="tag">' + t + "</span>"; }).join("") + "</div>";
  }
  function spark() {
    var pts = [28, 25, 30, 22, 26, 19, 24, 16, 20, 15], Ws = 152, Hs = 38, st = Ws / (pts.length - 1), mi = pts.indexOf(Math.min.apply(null, pts));
    var co = pts.map(function (v, i) { return [Math.round(i * st), Math.round(Hs - (v / 32 * Hs))]; });
    return '<svg class="spark" viewBox="0 0 ' + Ws + " " + Hs + '"><path d="M' + co.map(function (p) { return p[0] + "," + p[1]; }).join(" L") + '" fill="none" stroke="var(--coast)" stroke-width="2"/><circle cx="' + co[mi][0] + '" cy="' + co[mi][1] + '" r="3.5" fill="var(--accent)"/></svg>';
  }
  function compactHTML(c) { return photoHTML(c) + '<div class="hc-body">' + bodyTop(c) + '<div class="hc-cta">갈래 → 자세히 보기</div></div>'; }
  function compareHTML(links) {
    if (!links || !links.length) return "";
    return '<div class="hc-compare">' + links.map(function (l, i) {
      return '<a class="cmp' + (i === 0 ? " hero" : "") + '" href="' + l.url + '" target="_blank" rel="noopener sponsored">' +
        '<span class="cmp-name">' + l.name + '</span>' +
        '<span class="cmp-tag">' + l.tag + '</span>' +
        '<span class="cmp-go">최저가 보기 →</span></a>';
    }).join("") + "</div>";
  }
  function detailHTML(c) {
    return photoHTML(c) + '<div class="hc-body">' + bodyTop(c) +
      '<div class="hc-detail">' +
      '<div class="hc-sec">최근 가격 추이</div>' + spark() +
      '<div class="hc-sec">어디가 제일 싼지 비교해보세요</div>' + compareHTML(c.links) +
      '<div class="hc-ad">위 가격은 발견가(스캔 시점) · 실시간 최저가는 각 사이트에서 확인하세요 · 일부는 예약 시 수수료 (광고)</div>' +
      "</div></div>";
  }
  function positionCard(c) {
    if (window.innerWidth <= 860) { hc.style.left = ""; hc.style.top = ""; return; }  // 모바일=하단 시트(CSS)
    var cp = svgToClient(c.x, c.y), box = stageEl.getBoundingClientRect(), h = hc.offsetHeight;
    var left = cp.x - box.left, top = cp.y - box.top - 16 - h; if (top < 8) top = cp.y - box.top + 20;
    left = Math.max(120, Math.min(box.width - 120, left)); hc.style.left = left + "px"; hc.style.top = top + "px";
  }
  function showCard(i, scroll, expanded) {
    active = i; var c = cityByI(i); paintActive();
    if (!c || c.x == null) { hc.classList.remove("show"); return; }
    drawArc(c);
    hc.classList.toggle("expanded", !!expanded);
    hc.innerHTML = expanded ? detailHTML(c) : compactHTML(c);
    hc.classList.add("show"); positionCard(c);
    if (scroll) { var card = document.querySelector('.fcard[data-i="' + i + '"]'); if (card) card.scrollIntoView({ behavior: "smooth", block: "nearest", inline: "nearest" }); }
  }
  function highlight(i, scroll) { if (expandedI !== null) return; showCard(i, scroll, false); }
  function expand(i) { expandedI = i; showCard(i, true, true); }
  function clearHi() { if (expandedI !== null) return; active = null; paintActive(); hc.classList.remove("show"); if (arc.getTotalLength) { arc.style.transition = "stroke-dashoffset .2s ease"; arc.style.strokeDashoffset = arc.getTotalLength(); } }
  function collapse() { expandedI = null; active = null; paintActive(); hc.classList.remove("show", "expanded"); if (arc.getTotalLength) { arc.style.transition = "stroke-dashoffset .2s ease"; arc.style.strokeDashoffset = arc.getTotalLength(); } }
  hc.addEventListener("click", function (e) { e.stopPropagation(); if (expandedI === null && active !== null) expand(active); });

  // ---- 단계 · 필터 도크 ----
  function setStage(idx) { stageIdx = idx; collapse(); render(); var bs = document.querySelectorAll(".stagebar .pill"); for (var k = 0; k < bs.length; k++) bs[k].classList.toggle("on", k === idx); }
  var sbs = document.querySelectorAll(".stagebar .pill");
  for (var b = 0; b < sbs.length; b++) (function (el, idx) { el.addEventListener("click", function () { setStage(idx); }); })(sbs[b], b);
  stageEl.addEventListener("mouseleave", function () { if (matchMedia("(hover:hover)").matches) clearHi(); });
  svg.addEventListener("click", function (e) { if (e.target === svg || e.target.classList.contains("land")) collapse(); });

  if (bslider) { budget = +bslider.value; }
  function updCount() {
    var n = 0; if (dateMode && !(dateMode === "custom" && !dateCustom)) n++; if (mood) n++; if (budget < BUDGET_MAX) n++;
    var el = document.getElementById("fdcount"); if (el) el.textContent = n ? ("· " + n) : "";
  }
  var dateEls = document.querySelectorAll(".fchip.date"), customBox = document.getElementById("customdates");
  function setActiveDate(mode) { dateMode = mode; for (var k = 0; k < dateEls.length; k++) dateEls[k].classList.toggle("on", dateEls[k].dataset.date === mode); if (customBox) customBox.classList.toggle("show", mode === "custom"); }
  for (var di = 0; di < dateEls.length; di++) (function (el) { el.addEventListener("click", function () { setActiveDate(el.dataset.date); if (dateMode !== "custom") dateCustom = null; updCount(); collapse(); render(); }); })(dateEls[di]);
  var cds = document.getElementById("cdStart"), cde = document.getElementById("cdEnd");
  function readCustom() { var lo = cds && cds.value ? cds.value : "0000-00-00", hi = cde && cde.value ? cde.value : "9999-99-99"; dateCustom = (lo === "0000-00-00" && hi === "9999-99-99") ? null : [lo, hi]; }
  [cds, cde].forEach(function (inp) { if (inp) inp.addEventListener("change", function () { setActiveDate("custom"); readCustom(); updCount(); collapse(); render(); }); });
  var moodEls = document.querySelectorAll(".fchip.moodf");
  for (var mi = 0; mi < moodEls.length; mi++) (function (el) { el.addEventListener("click", function () { var m = el.dataset.mood; mood = (mood === m ? null : m); for (var k = 0; k < moodEls.length; k++) moodEls[k].classList.toggle("on", moodEls[k].dataset.mood === mood); updCount(); collapse(); render(); }); })(moodEls[mi]);
  if (bslider) bslider.addEventListener("input", function () { budget = +bslider.value; if (bval) bval.textContent = Math.round(budget / 10000) + "만"; updCount(); collapse(); render(); });
  var fdock = document.getElementById("fdock"), fdt = document.getElementById("fdtoggle");
  if (fdt) fdt.addEventListener("click", function () { fdock.classList.toggle("collapsed"); });
  if (fdock && window.innerWidth <= 860) fdock.classList.add("collapsed");  // 모바일=접힌 채 시작

  // ---- 화면0: 출발지 선택 ----
  function renderIntro() {
    var im = document.getElementById("introMap"); if (!im) return;
    var ip = d3.geoEquirectangular().rotate([-127.7, 0]).center([0, 35.9]).scale(3100).translate([200, 150]);
    var ipath = d3.geoPath(ip);
    var lp = document.createElementNS(SVGNS, "path"); lp.setAttribute("d", ipath(WORLD)); lp.setAttribute("class", "land"); im.appendChild(lp);
    Object.keys(D.origins).forEach(function (k) {
      var o = D.origins[k], p = ip([o.lon, o.lat]);
      var g = document.createElementNS(SVGNS, "g"); g.setAttribute("class", "ap");
      g.innerHTML = '<circle class="aph" cx="' + p[0] + '" cy="' + p[1] + '" r="14"/>' +
        '<circle class="apr" cx="' + p[0] + '" cy="' + p[1] + '" r="7"/>' +
        '<text class="aplabel" x="' + p[0] + '" y="' + (p[1] - 13) + '" text-anchor="middle">' + o.name + "</text>";
      g.addEventListener("click", function () { pickOrigin(k); });
      im.appendChild(g);
    });
  }
  function pickOrigin(k) {
    var o = D.origins[k]; ORIGIN = { n: o.name, lon: o.lon, lat: o.lat };
    CITY = D.deals.filter(function (dl) { return dl.o === k; }).map(toCity);
    var pill = document.getElementById("originPill"); if (pill) pill.textContent = o.name + " 출발 ▾";
    document.getElementById("intro").classList.add("hide");
    stageIdx = 0; expandedI = null; active = null; render();
  }
  var pill0 = document.getElementById("originPill");
  if (pill0) pill0.addEventListener("click", function () { document.getElementById("intro").classList.remove("hide"); });

  renderIntro();
})();
