/* 갈래말래 발견 홈 — 지도(무대) + '오늘의 발견' 카드 피드 + 필터 도크 + 확장 상세.
   데이터는 window.__DEALS(deals.json), 지도 윤곽은 window.__WORLD(geojson). d3-geo만 사용. */
(function () {
  "use strict";
  var D = window.__DEALS, WORLD = window.__WORLD;
  var svg = document.getElementById("map");
  if (!D || !WORLD || !svg || !window.d3 || !d3.geoEquirectangular) return;

  var SVGNS = "http://www.w3.org/2000/svg";
  var W = 1000, H = 680;
  // near·sea 는 고정. far 는 그날 딜 좌표에서 계산한다 — farView() 참조. (SPEC §CH1)
  var VIEWS = { near: { lon: 132, lat: 35.5, scale: 1500 },
                sea: { lon: 117, lat: 19, scale: 720 } };
  var FAR_LAT = 14, LABEL_PAD = 35, FAR_MIN_SCALE = 40;
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
      why: whyOf(dl), tags: dl.tags, g: grad(dl.tags), country: dl.country, links: dl.links || [], median: dl.median || 0 };
  }

  // ---- 파싱/공용 ----
  var LIGHT = [247, 178, 158], DEEP = [214, 60, 30];
  function lerp(a, b, t) { return Math.round(a + (b - a) * t); }
  function num(p) { return +p.replace(/[^0-9]/g, ""); }
  // 출발일 정렬 키 — 원본 ISO(YYYY-MM-DD)를 그대로 쓴다. 사전순 = 시간순.
  // 표시용 문자열("9/12(토)~")을 되파싱하면 연도가 없어 내년 딜이 앞으로 온다.
  function depkey(c) { return c.dep || "9999-99-99"; }
  function discNum(s) { return parseInt(s, 10) || 0; }

  svg.setAttribute("viewBox", "0 0 " + W + " " + H);

  // ---- 렌더 구조: 세계 path 는 한 번만 만들고, 뷰 변경은 transform 으로 한다 (B17) ----
  // geoEquirectangular 는 x = tx + s·λ, y = ty − s·φ 로 경위도에 선형이다. 따라서 rotate 만
  // 고정하면 center·scale 변경이 평면 아핀변환이 되어 path 를 다시 만들 필요가 없다.
  // 실측: path(WORLD) 재생성 15~17ms(전체 비용의 99.7%) → transform 문자열 0.00003ms.
  // 그대로 두면 400ms 트윈이 24프레임 x 16.8ms = 403ms 로 프레임 예산을 100% 먹는다.
  //
  // rotate 를 바꾸면 경도 이음매(±180°)가 움직여 어긋나므로(표본의 6~30%가 0.5px 초과),
  // 이음매를 **딜이 하나도 없는 최대 경도 구간 한가운데**에 못박는다. 로드 시 1회 계산.
  // 오늘 데이터로는 대서양 73.3°(뉴욕 -73.8° ~ 런던 -0.5°) 구간 → 이음매 -37.1°.
  // 남미 딜이 생기면 빈 구간이 바뀌지만 로드 시 계산이라 자동으로 따라간다.
  function seamRot() {
    var ls = [], seen = {}, i, k;
    for (k in D.origins) if (D.origins[k]) ls.push(D.origins[k].lon);
    for (i = 0; i < (D.deals || []).length; i++) ls.push(D.deals[i].lon);
    ls = ls.filter(function (v) { var q = (+v).toFixed(4); if (seen[q]) return false; seen[q] = 1; return true; })
           .sort(function (a, b) { return a - b; });
    if (ls.length < 2) return 143;
    var gap = -1, gStart = ls[0];
    for (i = 0; i < ls.length; i++) {
      var a = ls[i], b = ls[(i + 1) % ls.length], d = ((b - a) % 360 + 360) % 360;
      if (d > gap) { gap = d; gStart = a; }
    }
    return norm(norm(gStart + gap / 2) + 180);   // 빈 구간 한가운데가 ±180 에 오도록
  }
  var ROT = seamRot(), BASE = 200;
  // 기준 투영 — 절대 안 바뀐다. 여기서 만든 path 를 계속 재사용한다.
  var proj = d3.geoEquirectangular().rotate([-ROT, 0]).center([0, 0]).scale(BASE).translate([W / 2, H / 2]);
  var path = d3.geoPath(proj);
  var lands = document.getElementById("lands");
  var landPath = document.createElementNS(SVGNS, "path"); landPath.setAttribute("class", "land");
  lands.appendChild(landPath);
  landPath.setAttribute("d", path(WORLD));       // ← 이 호출이 전부다. 다시 안 부른다.

  // 뷰 → 아핀변환. 기준 평면의 점을 화면 좌표로 옮긴다.
  var XF = { k: 1, tx: 0, ty: 0 };
  function setXform(v) {
    var o = proj([v.lon, v.lat]), k = v.scale / BASE;
    XF = { k: k, tx: W / 2 - o[0] * k, ty: H / 2 - o[1] * k };
    lands.setAttribute("transform", "translate(" + XF.tx + "," + XF.ty + ") scale(" + XF.k + ")");
  }
  // 핀·라벨은 변환 그룹 **밖**에 있다 — 확대해도 점 크기와 글자 크기가 그대로여야 한다.
  function pt(lon, lat) { var p = proj([lon, lat]); return [p[0] * XF.k + XF.tx, p[1] * XF.k + XF.ty]; }
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
  function budgetOn() { return budget < BUDGET_MAX; }  // 슬라이더가 최대면 예산 필터는 꺼진 것
  function dimmed(c) { return (mood && c.tags.indexOf(mood) < 0) || (budgetOn() && num(c.price) > budget) || dateDim(c); }
  function anyFilter() { return mood || dateMode || budgetOn(); }

  function visibleCities() {
    var out = [];
    if (anyFilter()) {
      CITY.forEach(function (c, i) { c._i = i; out.push(c); });
    } else {
      // LOD — 무대 안에 들어오면 전부 그린다. 등급으로 숨기지 않는다. (SPEC §CH1, 2026-09-01 개정)
      // 숨기면 피드엔 있는데 지도엔 없는 딜이 생기고(F15), '더 멀리 갔는데 점이 줄어드는' 일이
      // 생긴다(대구 12→9). 밀도는 minor 핀을 낮춰서 푼다 — 지우지 않는다.
      // 무대 밖은 자연히 안 보이는 것이지 감추는 게 아니다. 축소할수록 늘기만 한다.
      var b = usableBand(), x0 = W / 2 - b.vbW / 2, x1 = W / 2 + b.vbW / 2,
          y0 = H / 2 - b.vbH / 2, y1 = H / 2 + b.vbH / 2;
      CITY.forEach(function (c, i) {
        var p = pt(c.lon, c.lat);
        if (p[0] < x0 || p[0] > x1 || p[1] < y0 || p[1] > y1) return;
        c._i = i; out.push(c);
      });
    }
    var cmp = { value: function (a, b) { return num(a.price) - num(b.price); },
                imminent: function (a, b) { var x = depkey(a), y = depkey(b); return x < y ? -1 : x > y ? 1 : 0; },
                discount: function (a, b) { return discNum(b.disc) - discNum(a.disc); } };
    out.sort(function (a, b) { var da = dimmed(a) ? 1 : 0, db = dimmed(b) ? 1 : 0; if (da !== db) return da - db; return cmp[sortMode](a, b); });
    return out;
  }
  // ---- '아주 멀리' 뷰: 중심·배율을 그날 딜에서 계산 (SPEC §CH1) ----
  // 경도를 정렬해 가장 큰 빈 구간을 찾고, 필요한 호 = 360 − 빈 구간, 중심 = 빈 구간의 정반대.
  // 고정값은 "오늘 데이터에서만 맞는 값"이라 목적지가 하나 늘고 줄 때마다 조용히 틀려진다.
  function norm(d) { return ((d + 180) % 360 + 360) % 360 - 180; }
  function farArc() {
    var ls = [], seen = {}, i;
    if (ORIGIN) ls.push(ORIGIN.lon);
    for (i = 0; i < CITY.length; i++) ls.push(CITY[i].lon);
    ls = ls.filter(function (v) { var k = v.toFixed(4); if (seen[k]) return false; seen[k] = 1; return true; })
           .sort(function (a, b) { return a - b; });
    if (ls.length < 2) return { arc: 60, lon: ls.length ? ls[0] : 127 };
    var gap = -1, gEnd = ls[0];
    for (i = 0; i < ls.length; i++) {
      var a = ls[i], b = ls[(i + 1) % ls.length], d = ((b - a) % 360 + 360) % 360;
      if (d > gap) { gap = d; gEnd = b; }
    }
    var arc = 360 - gap;
    return { arc: arc, lon: norm(gEnd + arc / 2) };   // 데이터 구간의 한가운데
  }
  // 무대에서 실제로 쓸 수 있는 띠 = 보이는 viewBox 가로에서 slice 크롭과 라벨 여유를 뺀 구간.
  // ⚠️ 필터 도크 폭은 빼지 않는다. 빼면 배율이 161→117로 줄어 지도가 화면의 46%밖에
  //    못 채운다(가로도 16% 빈다). 그 도크는 CH2에서 검색 한 줄(52px, 핀 0곳 가림)로
  //    교체가 확정돼 있어, 곧 사라질 것을 피하려고 지도를 30% 줄이는 셈이 된다.
  //    도크에 가려지는 핀은 B16으로 따로 열려 있다.
  function usableBand() {
    var box = stageEl.getBoundingClientRect(), cw = box.width || W, ch = box.height || H;
    var sf = Math.max(cw / W, ch / H);                 // preserveAspectRatio="slice" = cover
    var vbW = cw / sf, vbH = ch / sf;                  // 보이는 viewBox 크기
    return { vbW: vbW, vbH: vbH, half: Math.max(60, vbW / 2 - LABEL_PAD) };
  }
  function farView() {
    var a = farArc(), b = usableBand();
    // 단계는 갈수록 넓어져야 한다. 딜이 좁은 범위에 몰린 허브(제주: 호 33.5°)는 계산값이
    // 1376까지 올라가 '조금 더 멀리'(720)보다 더 확대돼 표시가 8→5로 줄었다. sea 배율로 막는다.
    var s = Math.min(VIEWS.sea.scale, Math.max(FAR_MIN_SCALE, b.half / (a.arc / 2 * Math.PI / 180)));
    // 지구 세로(πs)가 화면보다 짧으면 위아래에 바다만 남는다. 그럴 땐 지구를 세로 중앙에
    // 두어 여백이 위아래로 고르게 나뉘게 한다(적도 중심). 넘칠 땐 딜이 몰린 위도로 맞춘다.
    var lat = (Math.PI * s < b.vbH) ? 0 : FAR_LAT;
    return { lon: a.lon, lat: lat, scale: s };
  }
  function viewOf(stage) { return stage === "far" ? farView() : VIEWS[stage]; }

  function colorMaker(vis) {
    var vn = vis.map(function (c) { return num(c.price); }), lo = Math.min.apply(null, vn), hi = Math.max.apply(null, vn);
    return function (p) { var t = 1 - (num(p) - lo) / ((hi - lo) || 1);
      return "rgb(" + lerp(LIGHT[0], DEEP[0], t) + "," + lerp(LIGHT[1], DEEP[1], t) + "," + lerp(LIGHT[2], DEEP[2], t) + ")"; };
  }

  var PIN_R = 6, MINOR_R = 2.5;   // major 지름 12px · minor 지름 5px (SPEC §CH1)
  function render() {
    if (!ORIGIN) return;
    var v = viewOf(STAGES[stageIdx]);
    setXform(v);                                  // path 는 그대로 두고 transform 만 바꾼다
    var O = pt(ORIGIN.lon, ORIGIN.lat); ORIGIN.x = O[0]; ORIGIN.y = O[1];
    og.innerHTML = '<circle class="origin-ring" cx="' + O[0] + '" cy="' + O[1] + '" r="9"/>' +
      '<circle class="origin-dot" cx="' + O[0] + '" cy="' + O[1] + '" r="4"/>' +
      '<text class="plabel org" x="' + O[0] + '" y="' + (O[1] - 13) + '" text-anchor="middle">' + ORIGIN.n + " 출발</text>";
    var vis = visibleCities(), colorOf = colorMaker(vis);
    vis.forEach(function (c) { var p = pt(c.lon, c.lat); c.x = p[0]; c.y = p[1]; c._col = colorOf(c.price); });
    pins.innerHTML = "";
    vis.forEach(function (c) {
      // minor 는 지우지 않고 낮춘다 — 작게·반투명·후광 없음. 라벨도 major 만 단다.
      var mn = c.tier === "minor", r = mn ? MINOR_R : PIN_R;
      var g = document.createElementNS(SVGNS, "g");
      g.setAttribute("class", "pin" + (mn ? " minor" : "") + (dimmed(c) ? " dim" : "")); g.dataset.i = c._i;
      g.innerHTML = (mn ? "" : '<circle class="halo" cx="' + c.x + '" cy="' + c.y + '" r="' + (PIN_R * 1.6) + '" fill="' + c._col + '"/>') +
        '<circle class="core" cx="' + c.x + '" cy="' + c.y + '" r="' + r + '" fill="' + c._col + '"/>' +
        (mn ? "" : '<text class="plabel" x="' + c.x + '" y="' + (c.y + PIN_R + 11) + '" text-anchor="middle">' + c.n + "</text>");
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
    matches.forEach(function (c) { if (!heroCity || discNum(c.disc) > discNum(heroCity.disc) || (discNum(c.disc) === discNum(heroCity.disc) && depkey(c) < depkey(heroCity))) heroCity = c; });
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
    syncStepper();
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
  function priceCompare(c) {
    // 실데이터: 평소 시세(중앙값) 대비 발견가. 할인 없으면 생략.
    var now = num(c.price), med = c.median || 0;
    if (!med || med <= now) return "";
    var w = Math.max(12, Math.round(now / med * 100)), pct = Math.round((med - now) / med * 100);
    return '<div class="hc-sec">평소 시세와 비교</div>' +
      '<div class="pc">' +
      '<div class="pc-row"><span>평소 시세(중앙값)</span><span>₩' + med.toLocaleString("en-US") + "</span></div>" +
      '<div class="pc-bar"><div class="pc-fill" style="width:' + w + '%"></div></div>' +
      '<div class="pc-row now"><span>발견가</span><span>₩' + c.price + " · " + pct + "%↓</span></div>" +
      "</div>";
  }
  function compactHTML(c) { return photoHTML(c) + '<div class="hc-body">' + bodyTop(c) + '<div class="hc-cta">갈래 → 자세히 보기</div></div>'; }
  function compareHTML(links) {
    if (!links || !links.length) return "";
    return '<div class="hc-compare">' + links.map(function (l) {
      return '<a class="cmp" href="' + l.url + '" target="_blank" rel="noopener sponsored">' +
        '<span class="cmp-name">' + l.name + '</span>' +
        '<span class="cmp-go">최저가 보기 →</span></a>';
    }).join("") + "</div>";
  }
  function detailHTML(c) {
    return photoHTML(c) + '<div class="hc-body">' + bodyTop(c) +
      '<div class="hc-detail">' +
      priceCompare(c) +
      '<div class="hc-sec">어디가 제일 싼지 비교해보세요</div>' + compareHTML(c.links) +
      '<div class="hc-ad">위 가격은 발견가(스캔 시점) · 실시간 최저가는 각 사이트에서 확인하세요 · 일부는 예약 시 수수료 (광고)</div>' +
      "</div></div>";
  }
  function positionCard(c) {
    if (window.innerWidth <= 860) { hc.style.left = ""; hc.style.top = ""; hc.style.maxHeight = ""; return; }  // 모바일=하단 시트(CSS)
    var cp = svgToClient(c.x, c.y), box = stageEl.getBoundingClientRect(), h = hc.offsetHeight;
    var maxH = box.height - 16;
    if (h > maxH) { hc.style.maxHeight = maxH + "px"; hc.style.overflowY = "auto"; h = maxH; }
    else { hc.style.maxHeight = ""; hc.style.overflowY = ""; }
    var left = cp.x - box.left, top = cp.y - box.top - 16 - h;
    if (top < 8) {  // 위로 안 들어가면 아래로, 그래도 넘치면 무대 안에 고정
      top = cp.y - box.top + 20;
      if (top + h > box.height - 8) top = Math.max(8, box.height - 8 - h);
    }
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
  // 무대 종횡비가 1000/680을 넘나들면 가시 가로가 통째로 바뀐다 → far 배율을 다시 잡는다.
  var rzT = null;
  window.addEventListener("resize", function () {
    if (rzT) clearTimeout(rzT);
    rzT = setTimeout(function () { rzT = null; if (ORIGIN) render(); }, 120);
  });
  var sbs = document.querySelectorAll(".stagebar .pill");
  for (var b = 0; b < sbs.length; b++) (function (el, idx) { el.addEventListener("click", function () { setStage(idx); }); })(sbs[b], b);
  // 단계 스테퍼 — 줌이 아니라 한 단계씩 넘기는 버튼. 양 끝에서는 비활성. (SPEC §CH1)
  var stepEls = document.querySelectorAll(".stepper button");
  function stepDelta(el) { return el.getAttribute("data-step") === "out" ? 1 : -1; }
  function syncStepper() {
    for (var k = 0; k < stepEls.length; k++) {
      var n = stageIdx + stepDelta(stepEls[k]);
      stepEls[k].disabled = (n < 0 || n >= STAGES.length);
    }
  }
  for (var z = 0; z < stepEls.length; z++) (function (el) {
    el.addEventListener("click", function () {
      var n = stageIdx + stepDelta(el);
      if (n < 0 || n >= STAGES.length) return;
      setStage(n);
    });
  })(stepEls[z]);
  syncStepper();
  stageEl.addEventListener("mouseleave", function () { if (matchMedia("(hover:hover)").matches) clearHi(); });
  svg.addEventListener("click", function (e) { if (e.target === svg || e.target.classList.contains("land")) collapse(); });

  if (bslider) { budget = +bslider.value; }
  function updCount() {
    var n = 0; if (dateMode && !(dateMode === "custom" && !dateCustom)) n++; if (mood) n++; if (budgetOn()) n++;
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
