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
  var BUDGET_MAX = 1000000;   // 출발지를 고를 때 데이터에서 다시 잡는다 — resetBudget()

  var ORIGIN = null, CITY = [], stageIdx = 0, active = null, expandedI = null;
  var sortMode = "value", mood = null, dateMode = "", dateCustom = null, nightsMode = "", budget = 1e12;

  // ---- 날짜 필터 — 날짜를 다시 계산하지 않고 `when` 값으로 거른다 (SPEC §CH2, B26) ----
  // 프론트가 "이번 주"를 따로 계산하면 백엔드의 `when` 계산과 갈라진다. 실제로 갈라졌다 —
  // 백엔드는 라벨이 틀렸고(`이번 주말`이 다음 주말에 붙음) 프론트는 필터가 틀렸다.
  // 실측: 일요일에 `이번 주`를 누르면 정상 0건인데 18건(전부 다음 주), 토요일에 `이번 주말`을
  // 누르면 오늘·내일 출발 10건이 사라졌다. 원인이 같은데 두 곳에서 따로 터진 것이다.
  // `when` 으로 거르면 카드 배지와 필터가 구조적으로 어긋날 수 없다.
  var WHEN_CHIPS = ["이번 주말", "다음 주말", "이번 주", "이번 달", "다음 달"];
  function matchesDate(c, mode) {
    if (!mode) return true;                                   // 아무때
    if (mode === "custom") {                                  // 여기서만 날짜를 본다
      if (!dateCustom) return true;
      return c.dep >= dateCustom[0] && c.dep <= dateCustom[1];
    }
    if (mode === "rest") return WHEN_CHIPS.indexOf(c.when) < 0;   // N월·내년 N월·YYYY년 N월
    return c.when === mode;
  }
  function dateDim(c) { return !matchesDate(c, dateMode); }

  // ---- 며칠 축 — `nights` 를 쓴다 (SPEC §CH2) ----
  // 주말 2박3일과 일주일 휴가는 전혀 다른 여행인데 지금까지 가를 수가 없었다.
  // 편도·불명이면 `nights` 가 "" 다 — 어느 칩에도 걸리지 않는다. 모르는 걸 안다고 하지 않는다.
  var NIGHT_BANDS = { "1-3": [1, 3], "4-6": [4, 6], "7-13": [7, 13], "14+": [14, 9999] };
  function nightsOf(c) { var m = /(\d+)박/.exec(c.nights || ""); return m ? +m[1] : null; }
  function matchesNights(c, mode) {
    if (!mode) return true;                       // 상관없어
    var b = NIGHT_BANDS[mode]; if (!b) return true;
    var n = nightsOf(c);
    return n !== null && n >= b[0] && n <= b[1];
  }
  function budgetOn() { return budget < BUDGET_MAX; }  // 슬라이더가 최대면 예산 필터는 꺼진 것
  // 최대치는 "제한 없음"이다. 부수 효과로 `155만` 같은 어색한 숫자가 화면에 안 나온다. (SPEC §CH2)
  function budgetLabel() { return budgetOn() ? Math.round(budget / 10000) + "만 이하" : "제한 없음"; }
  // 슬라이더 범위를 **현재 출발지 데이터**에서 만든다 (B5).
  // 고정 100만이면 실제 최고가(138만)를 넘는 딜을 걸러낼 수만 있고 되살릴 수 없었다 —
  // 슬라이더를 끝까지 올려도 안 돌아온다. min 을 최저가에서 올림하는 이유는
  // 맨 왼쪽까지 내려도 최소 1건은 남게 하려는 것이다(조작만으로 0건을 만들 수 없게).
  var STEP = 50000;
  function resetBudget() {
    if (!bslider || !CITY.length) return;
    var lo = Infinity, hi = 0, i, v;
    for (i = 0; i < CITY.length; i++) { v = num(CITY[i].price); if (v < lo) lo = v; if (v > hi) hi = v; }
    var mn = Math.ceil(lo / STEP) * STEP, mx = Math.ceil(hi / STEP) * STEP;
    if (mx <= mn) mx = mn + STEP;                       // 딜이 1건뿐인 허브에서도 트랙이 성립하게
    bslider.min = mn; bslider.max = mx; bslider.step = STEP; bslider.value = mx;
    BUDGET_MAX = mx; budget = mx;                        // 최대치 = 필터 꺼짐
    if (bval) bval.textContent = budgetLabel();
  }
  function dimmed(c) { return (mood && c.tags.indexOf(mood) < 0) || (budgetOn() && num(c.price) > budget) || dateDim(c) || !matchesNights(c, nightsMode); }
  function anyFilter() { return mood || dateMode || nightsMode || budgetOn(); }

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

  function matchCount(vis) { var n = 0; for (var i = 0; i < vis.length; i++) if (!dimmed(vis[i])) n++; return n; }
  // 필터 중에는 단계 버튼을 **치운다** — 비활성으로 두지 않는다. 필터 중에는 "거리 단계"라는
  // 개념 자체가 성립하지 않기 때문이다. 자리에는 `전 지역에서 찾는 중` 한 줄이 들어간다.
  function syncStageBar() {
    var bar = document.querySelector(".stagebar"); if (!bar) return;
    var on = anyFilter();
    bar.classList.toggle("allregions", on);
    var note = bar.querySelector(".allnote");
    if (on && !note) { note = document.createElement("span"); note.className = "allnote"; note.textContent = "전 지역에서 찾는 중"; bar.appendChild(note); }
  }
  // ---- 카드 태그: "사진이 큰 자리에만, 사진 위에" (SPEC §CH2, 2026-09-01 확정) ----
  // 표시 태그 = **하위 전부 + 상위 1개**(하위 없으면 상위 2개), 최대 4개.
  // 개수를 고정하지 않는다 — 태그 개수가 곧 "즐길 게 얼마나 많은가"라는 신호다.
  // 하위는 반드시 상위를 동반하므로 `야시장`을 보고 `미식` 필터를 눌러도 잡힌다.
  var TAG_TOP = ["해변", "도시", "미식", "자연", "문화", "온천"];
  function cardTags(tags) {
    var sub = [], top = [], i;
    for (i = 0; i < tags.length; i++) (TAG_TOP.indexOf(tags[i]) < 0 ? sub : top).push(tags[i]);
    return (sub.length ? sub.concat(top.slice(0, 1)) : top.slice(0, 2)).slice(0, 4);
  }
  function ovTags(c) {
    var t = cardTags(c.tags);
    return t.length ? '<div class="phtags">' + t.map(function (x) { return '<span class="ovtag">' + x + "</span>"; }).join("") + "</div>" : "";
  }
  var PIN_R = 6, MINOR_R = 2.5;   // major 지름 12px · minor 지름 5px (SPEC §CH1)

  // ---- 라벨 겹침 회피: 4방향 후보 + 실패 시 라벨만 생략 (SPEC §CH1, B3/B15) ----
  // 아래 한 자리만 쓰면 `도하`+`두바이`가 `도하바이`로 붙고 가장자리에서 `칭다오`가 `다오`로 잘렸다.
  var LAB_FS = 13;
  // 라벨 폭은 글자수 × 폰트크기 × 0.95 추정으로 충분하다(정밀 측정 불필요 — SPEC).
  function labW(t) { return t.length * LAB_FS * 0.95; }
  // 후보 4자리를 순서대로: 아래 → 위 → 오른쪽 → 왼쪽.
  // 아래가 기본인 이유: 현행 동작이고, 핀 위쪽은 항로 곡선이 지나간다.
  function labSpots(c) {
    // 실측: 라벨은 paint-order stroke 3px 를 두르고 있어 getBBox 높이가 15.8 나온다(폰트 13).
    // 높이를 13으로 잡으면 세로 겹침이 새어 나간다. 위로 뻗는 양은 글자 위쪽 + 외곽선 절반.
    var w = labW(c.n), h = LAB_FS + 3, up = LAB_FS * 0.8 + 1.5, gap = PIN_R + 5;
    return [
      { x: c.x, y: c.y + PIN_R + 11, anchor: "middle", l: c.x - w / 2, t: c.y + PIN_R + 11 - up },
      { x: c.x, y: c.y - gap,        anchor: "middle", l: c.x - w / 2, t: c.y - gap - up },
      { x: c.x + gap, y: c.y + 4,    anchor: "start",  l: c.x + gap,   t: c.y + 4 - up },
      { x: c.x - gap, y: c.y + 4,    anchor: "end",    l: c.x - gap - w, t: c.y + 4 - up }
    ].map(function (s) { s.w = w; s.h = h; s.dx = s.x - c.x; s.dy = s.y - c.y; return s; });
  }
  // 사각형이 안 겹쳐도 여백이 0이면 두 단어가 한 단어처럼 읽힌다(`홍콩상하이`).
  // 충돌 판정에 최소 간격을 준다 — 배치 실패(생략)가 조금 늘지만 읽히는 게 먼저다.
  var LAB_GAP_X = 4, LAB_GAP_Y = 2;
  function hits(a, b) {
    return a.l - LAB_GAP_X < b.l + b.w && b.l - LAB_GAP_X < a.l + a.w &&
           a.t - LAB_GAP_Y < b.t + b.h && b.t - LAB_GAP_Y < a.t + a.h;
  }
  // 도크·줌 버튼이 덮는 사각형은 라벨 자리에서 제외한다 — 무대 밖 처리와 같다. (SPEC §CH2, B16)
  // 화면 좌표 → viewBox 좌표는 CTM 역행렬로 옮긴다. slice 배율을 손으로 다시 계산하지 않는다.
  function clientToVb(x, y) { var p = svg.createSVGPoint(); p.x = x; p.y = y; return p.matrixTransform(svg.getScreenCTM().inverse()); }
  // 도크는 **펼친 상태 기준**으로 잰다 — 접었다 펼 때마다 라벨이 재배치되면 산만하다(SPEC §CH2).
  // 접혀 있으면 클래스를 잠깐 떼고 재서 되돌린다. 같은 태스크 안이라 화면엔 안 나타난다.
  function uiBoxes() {
    var out = [], els = [document.getElementById("fdock"), document.getElementById("stepper")];
    for (var i = 0; i < els.length; i++) {
      var e = els[i]; if (!e) continue;
      var col = e.classList.contains("collapsed");
      if (col) e.classList.remove("collapsed");
      var r = e.getBoundingClientRect();
      if (col) e.classList.add("collapsed");
      if (!r.width || !r.height) continue;
      var a = clientToVb(r.left, r.top), b = clientToVb(r.right, r.bottom);
      out.push({ l: a.x, t: a.y, w: b.x - a.x, h: b.y - a.y });
    }
    return out;
  }
  function placeLabels(vis) {
    var band = usableBand(),
        x0 = W / 2 - band.vbW / 2, x1 = W / 2 + band.vbW / 2,
        y0 = H / 2 - band.vbH / 2, y1 = H / 2 + band.vbH / 2;
    var placed = uiBoxes();                     // UI 사각형을 미리 놓아 그 자리를 못 쓰게 한다
    // 배치 순서 = 우선순위: major 먼저, 같은 등급이면 가격 낮은 순. 싼 딜이 우리가 파는 것이다.
    // 라벨은 major 에게만, 그리고 **필터 중에는 매칭에게만** 준다.
    // 밀도를 만드는 건 점이 아니라 글자다 — 비매칭을 LOD 로 추려도 59→44개로 효과가 없는데,
    // 라벨을 매칭에게만 주면 매칭 라벨이 거의 다 살아남는다(실측 84~100%). (SPEC §CH2)
    var filtering = anyFilter();
    var cands = vis.filter(function (c) { return c.tier !== "minor" && !(filtering && dimmed(c)); })
                   .sort(function (a, b) { return num(a.price) - num(b.price); });
    vis.forEach(function (c) { c._lab = null; });
    cands.forEach(function (c) {
      var spots = labSpots(c), i, s, j, ok;
      for (i = 0; i < spots.length; i++) {
        s = spots[i];
        // 후보가 무대를 벗어나면 건너뛴다 ← 이것이 가장자리 클램프다.
        if (s.l < x0 || s.l + s.w > x1 || s.t < y0 || s.t + s.h > y1) continue;
        for (j = 0, ok = true; j < placed.length; j++) if (hits(s, placed[j])) { ok = false; break; }
        if (ok) { c._lab = s; placed.push(s); return; }
      }
      // 넷 다 실패하면 라벨만 생략한다. 핀은 반드시 남는다 — 딜을 지우는 게 아니다.
      // 자리는 기본 후보로 들고 있다가 활성(호버/선택) 시에만 덮어 그린다.
      c._lab = spots[0]; c._lab.off = true;
    });
  }
  function render() {
    if (!ORIGIN) return;
    tweenId++; svg.classList.remove("tweening");  // 진행 중 트윈이 있으면 무효화
    // 필터 중에는 항상 `아주 멀리` 뷰다. "전 지역 매칭"이 확정 스펙인데 가까운 단계에서
    // 필터를 켜면 매칭 딜이 화면 밖에 있다 — 피드엔 뜨는데 지도엔 없는 상태(F15)가 재현된다.
    // 실측(서울 `해변` 22건): 화면 안이 가까운 곳 10 · 조금 더 멀리 16 · 아주 멀리 22. (SPEC §CH2)
    var v = viewOf(anyFilter() ? "far" : STAGES[stageIdx]);
    setXform(v); CURV = v;                        // path 는 그대로 두고 transform 만 바꾼다
    var O = pt(ORIGIN.lon, ORIGIN.lat); ORIGIN.x = O[0]; ORIGIN.y = O[1];
    og.innerHTML = '<circle class="origin-ring" cx="' + O[0] + '" cy="' + O[1] + '" r="9"/>' +
      '<circle class="origin-dot" cx="' + O[0] + '" cy="' + O[1] + '" r="4"/>' +
      '<text class="plabel org" x="' + O[0] + '" y="' + (O[1] - 13) + '" text-anchor="middle">' + ORIGIN.n + " 출발</text>";
    var vis = visibleCities(), colorOf = colorMaker(vis);
    vis.forEach(function (c) { var p = pt(c.lon, c.lat); c.x = p[0]; c.y = p[1]; c._col = colorOf(c.price); });
    placeLabels(vis);
    pins.innerHTML = "";
    vis.forEach(function (c) {
      // minor 는 지우지 않고 낮춘다 — 작게·반투명·후광 없음. 라벨도 major 만 단다.
      var mn = c.tier === "minor", r = mn ? MINOR_R : PIN_R;
      var g = document.createElementNS(SVGNS, "g");
      g.setAttribute("class", "pin" + (mn ? " minor" : "") + (dimmed(c) ? " dim" : "")); g.dataset.i = c._i;
      var L = c._lab;
      g.innerHTML = (mn ? "" : '<circle class="halo" cx="' + c.x + '" cy="' + c.y + '" r="' + (PIN_R * 1.6) + '" fill="' + c._col + '"/>') +
        '<circle class="core" cx="' + c.x + '" cy="' + c.y + '" r="' + r + '" fill="' + c._col + '"/>' +
        (L ? '<text class="plabel' + (L.off ? " off" : "") + '" x="' + L.x + '" y="' + L.y +
             '" text-anchor="' + L.anchor + '">' + c.n + "</text>" : "");
      (function (el, i) { el.addEventListener("mouseenter", function () { highlight(i, true); });
        el.addEventListener("click", function (e) { e.stopPropagation(); expand(i); }); })(g, c._i);
      pins.appendChild(g);
    });
    // 카드 피드
    feed.innerHTML = '<div class="feedhead"><div class="fh-top"><b>오늘의 발견</b><span>' +
      (anyFilter() ? "조건에 맞는 " + matchCount(vis) + "곳" : ORIGIN.n + " 출발 · " + vis.length + "곳") + "</span></div>" +
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
        // 작은 썸네일(62px)엔 태그를 안 넣는다 — 사진이 태그를 담기엔 작다.
        // 히어로(104px 전폭)에만 사진 위로 얹는다. 그래서 작은 카드가 세로를 20% 덜 먹는다.
        '<div class="thumb" style="background:' + c.g + '">' + (hero ? '<span class="pick">진짜 갈래말래?</span>' + ovTags(c) : "") + "</div>" +
        '<div class="fbody"><div class="frow"><b class="fcity">' + c.n + '</b><span class="stamp">' + c.disc + "</span></div>" +
        '<div class="fprice"><small>₩</small>' + c.price + ' <span class="tilde">~</span></div>' +
        '<div class="fdate"><span class="when">' + c.when + "</span>" + c.date + (c.nights ? " · " + c.nights : "") + "</div>" +
        '<div class="fwhy">' + c.why + "</div>" +
        (hero ? '<div class="gorow"><button class="go">갈래 → 자세히 보기</button></div>' : "") +
        "</div>";
      (function (el, i) { el.addEventListener("mouseenter", function () { highlight(i, false); });
        el.addEventListener("click", function () { expand(i); }); })(card, c._i);
      feed.appendChild(card);
    });
    var sps = feed.querySelectorAll(".spill");
    for (var s = 0; s < sps.length; s++) (function (el) { el.addEventListener("click", function () { sortMode = el.dataset.sort; collapse(); render(); }); })(sps[s]);
    if (active !== null) paintActive();
    syncStepper(); syncDateChips(); syncNightChips(); syncMoodChips(); syncStageBar();
  }

  // ---- 전환 트윈 (SPEC §CH1 / B2) ----
  // render() 는 목적지 뷰로 전부 그린다. 트윈은 그 위에서 **좌표만** 움직인다 —
  // path 는 T5 덕에 transform 한 줄이고, 핀은 cx/cy 만 고치면 되므로 DOM 재생성이 없다.
  var CURV = null, tweenId = 0;
  function reduceMotion() {
    return window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  }
  // 좌표만 갱신하는 가벼운 경로. 라벨·항로는 트윈 중 숨기므로 건드리지 않는다.
  function moveOnly(v) {
    setXform(v); CURV = v;
    var O = pt(ORIGIN.lon, ORIGIN.lat); ORIGIN.x = O[0]; ORIGIN.y = O[1];
    var oc = og.childNodes, i;
    for (i = 0; i < oc.length; i++) {
      if (oc[i].tagName === "circle") { oc[i].setAttribute("cx", O[0]); oc[i].setAttribute("cy", O[1]); }
      else if (oc[i].tagName === "text") { oc[i].setAttribute("x", O[0]); oc[i].setAttribute("y", O[1] - 13); }
    }
    var gs = pins.childNodes;
    for (i = 0; i < gs.length; i++) {
      var c = cityByI(+gs[i].dataset.i); if (!c) continue;
      var p = pt(c.lon, c.lat); c.x = p[0]; c.y = p[1];
      var kids = gs[i].childNodes;
      for (var j = 0; j < kids.length; j++) {
        if (kids[j].tagName === "circle") { kids[j].setAttribute("cx", p[0]); kids[j].setAttribute("cy", p[1]); }
        else if (kids[j].tagName === "text") {   // 배치된 자리를 유지한다 — 트윈이 라벨을 아래로 되돌리면 안 된다
          var L = c._lab || { dx: 0, dy: PIN_R + 11 };
          kids[j].setAttribute("x", p[0] + L.dx); kids[j].setAttribute("y", p[1] + L.dy);
        }
      }
    }
  }
  function tweenTo(from, to, ms) {
    var id = ++tweenId, t0 = 0;
    // 배율은 반드시 로그 보간 — 선형이면 1500→182 같은 큰 변화에서 초반에 확 튀고 후반에 긴다.
    var dLon = norm(to.lon - from.lon), ratio = to.scale / from.scale;
    svg.classList.add("tweening");                 // 트윈 중 라벨·항로 숨김
    moveOnly(from);   // 첫 프레임을 기다리지 않고 즉시 출발점으로. 안 하면 render()가 그린
                      // 목적지가 한 번 번쩍였다가 되돌아간다(rAF 는 다음 프레임에야 돈다).
    // 안전장치 — rAF 가 안 도는 상황(탭 전환·백그라운드)에서도 반드시 목적지에서 끝낸다.
    // 없으면 라벨·항로가 숨겨진 채 출발점에 멈춰 있게 된다.
    var guard = setTimeout(function () { if (id === tweenId) finish(); }, ms + 200);
    // 끝낼 때 tweenId 를 올려 **이미 예약된 rAF 를 무효화**한다. 안 하면 안전장치가 목적지에
    // 안착시킨 뒤 뒤늦게 도착한 프레임이 지도를 중간 위치로 되돌린다(실측: 배율 182 → 380).
    function finish() { clearTimeout(guard); tweenId++; moveOnly(to); svg.classList.remove("tweening"); }
    function step(now) {
      if (id !== tweenId) { clearTimeout(guard); return; }   // 새 트윈이 가로챘다 — 큐에 쌓지 않는다
      if (!t0) t0 = now;
      var t = Math.min(1, (now - t0) / ms), e = 1 - Math.pow(1 - t, 3);   // cubic-out
      moveOnly({ lon: from.lon + dLon * e, lat: from.lat + (to.lat - from.lat) * e,
                 scale: from.scale * Math.pow(ratio, e) });
      if (t < 1) requestAnimationFrame(step);
      else finish();
    }
    requestAnimationFrame(step);
  }

  // ---- 항로 + 플로팅/확장 카드 ----
  function cityByI(i) { for (var k = 0; k < CITY.length; k++) if (CITY[k]._i === i && CITY[k].x != null) return CITY[k]; return CITY[i]; }
  function paintActive() {
    var ps = document.querySelectorAll(".pin"), act = null;
    for (var k = 0; k < ps.length; k++) {
      var on = +ps[k].dataset.i === active;
      ps[k].classList.toggle("act", on); if (on) act = ps[k];
    }
    // 활성 핀은 맨 뒤로 옮겨 그 위에 덮어 그린다. 다른 라벨을 흐트러뜨리지 않는다(재배치 없음).
    if (act && act.nextSibling) pins.appendChild(act);
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
  function photoHTML(c) { return '<div class="hc-photo" style="background:' + c.g + '"><span class="ph-tag">사진 준비중</span>' + ovTags(c) + '<span class="cityname">' + c.n + "</span></div>"; }
  function bodyTop(c) {
    return '<div class="hc-row"><span class="hc-price"><small>₩</small>' + c.price + ' <span class="tilde">~</span></span><span class="stamp">특가 ' + c.disc + "</span></div>" +
      '<div class="hc-date">' + c.date + (c.nights ? " · " + c.nights : "") + "</div>" +
      '<div class="hc-why">' + c.why + "</div>";
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
  // 제휴 링크가 실제로 있을 때만 (광고) 설명줄을 띄운다. 없는 날 "(광고) 표시는…"이 뜨면
  // 화면에 없는 표시를 설명하는 꼴이 된다.
  function adLinks(links) {
    for (var i = 0; i < (links || []).length; i++) if (links[i].ad) return true;
    return false;
  }
  function compareHTML(links) {
    if (!links || !links.length) return "";
    return '<div class="hc-compare">' + links.map(function (l) {
      // (광고)는 `ad` 가 참인 링크에만 붙인다 — 이름·순서·URL 모양으로 추측하지 않는다.
      // `tag`(전체 비교·한국 인기·중립·한국어)는 우리가 매기는 평가라 계속 숨긴다. (COPY.md 제휴 고지)
      // 시각적으로 약하게 둔다 — 눈에 띄게 만들면 고지가 아니라 강조가 된다.
      return '<a class="cmp" href="' + l.url + '" target="_blank" rel="noopener sponsored">' +
        '<span class="cmp-name">' + l.name + (l.ad ? ' <span class="cmp-ad">(광고)</span>' : "") + '</span>' +
        '<span class="cmp-go">최저가 보기 →</span></a>';
    }).join("") + "</div>";
  }
  function detailHTML(c) {
    return photoHTML(c) + '<div class="hc-body">' + bodyTop(c) +
      '<div class="hc-detail">' +
      priceCompare(c) +
      '<div class="hc-sec">어디가 제일 싼지 비교해보세요</div>' + compareHTML(c.links) +
      '<div class="hc-ad">위 가격은 발견가(스캔 시점) · 실시간 최저가는 각 사이트에서 확인하세요' +
      (adLinks(c.links) ? '<br>(광고) 표시는 예약하시면 저희가 수수료를 받는 링크예요 · 가격은 같아요' : "") + "</div>" +
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
  // 필터를 켜고 끌 때도 단계 전환과 같은 모션으로 움직인다(400ms · cubic-out · 배율 로그 보간).
  // 필터를 끄면 stageIdx 가 그대로라 직전 단계로 돌아온다. (SPEC §CH2)
  function applyFilter() {
    var from = CURV;
    updCount(); collapse(); render();
    if (from && CURV && !reduceMotion() && from.scale !== CURV.scale) tweenTo(from, CURV, 400);
  }
  function setStage(idx) {
    var from = CURV;                              // 지금 화면에 적용된 뷰
    stageIdx = idx; collapse(); render();         // 목적지 단계의 딜 집합·좌표로 전부 그린다
    var bs = document.querySelectorAll(".stagebar .pill");
    for (var k = 0; k < bs.length; k++) bs[k].classList.toggle("on", k === idx);
    // 전환 중 다른 단계를 누르면 진행 중인 트윈을 버리고 **현재 위치에서** 새 목표로 간다.
    if (from && CURV && !reduceMotion()) tweenTo(from, CURV, 400);
  }
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

  // 초기 예산값은 출발지를 고를 때 resetBudget() 이 잡는다.
  function updCount() {
    // 접힌 도크는 **개수가 아니라 조건**을 보여준다 — 목적이 "지금 뭐가 걸려 있나"이고
    // 개수는 그 답이 아니다. 순서는 도크 안 순서 그대로(날짜 → 며칠 → 분위기 → 예산).
    // 최대 2개까지 쓰고 넘치면 `외 N`. 아무것도 없으면 그냥 `필터`. (SPEC §CH2, B7)
    var on = [], el;
    if (dateMode && !(dateMode === "custom" && !dateCustom)) {
      for (var k = 0; k < dateEls.length; k++)
        if (dateEls[k].getAttribute("data-date") === dateMode) { on.push(dateEls[k].firstChild.nodeValue.trim()); break; }
    }
    if (nightsMode) {
      for (var q = 0; q < nightEls.length; q++)
        if (nightEls[q].getAttribute("data-nights") === nightsMode) { on.push(nightEls[q].firstChild.nodeValue.trim()); break; }
    }
    if (mood) on.push(mood);
    if (budgetOn()) on.push(budgetLabel());
    el = document.getElementById("fdsum");
    if (el) el.textContent = on.length ? (on.slice(0, 2).join(" · ") + (on.length > 2 ? " 외 " + (on.length - 2) : "")) : "필터";
  }
  var dateEls = document.querySelectorAll(".fchip.date"), customBox = document.getElementById("customdates");
  // 누르기 전에 건수를 보인다. 0곳이면 흐리게 하고 못 누르게 한다 — 0곳이 될 칩을 누르게 두지 않는다.
  // 일요일에 `이번 주`가 0곳이 되는 건 정상이고, 건수가 화면에서 스스로 설명한다. (SPEC §CH2)
  function syncDateChips() {
    for (var k = 0; k < dateEls.length; k++) {
      var el = dateEls[k], m = el.getAttribute("data-date"), cnt = el.querySelector("i");
      if (!m || m === "custom") continue;                     // 아무때·날짜 지정은 건수를 안 센다
      var n = 0;
      for (var i = 0; i < CITY.length; i++) if (matchesDate(CITY[i], m)) n++;
      if (cnt) cnt.textContent = n + "곳";
      el.disabled = (n === 0 && dateMode !== m);               // 이미 고른 칩은 되돌릴 수 있게 남긴다
      el.classList.toggle("empty", n === 0);
    }
  }
  function setActiveDate(mode) { dateMode = mode; for (var k = 0; k < dateEls.length; k++) dateEls[k].classList.toggle("on", dateEls[k].getAttribute("data-date") === mode); if (customBox) customBox.classList.toggle("show", mode === "custom"); }
  for (var di = 0; di < dateEls.length; di++) (function (el) { el.addEventListener("click", function () { if (el.disabled) return; setActiveDate(el.getAttribute("data-date")); if (dateMode !== "custom") dateCustom = null; applyFilter(); }); })(dateEls[di]);
  var cds = document.getElementById("cdStart"), cde = document.getElementById("cdEnd");
  function readCustom() { var lo = cds && cds.value ? cds.value : "0000-00-00", hi = cde && cde.value ? cde.value : "9999-99-99"; dateCustom = (lo === "0000-00-00" && hi === "9999-99-99") ? null : [lo, hi]; }
  [cds, cde].forEach(function (inp) { if (inp) inp.addEventListener("change", function () { setActiveDate("custom"); readCustom(); applyFilter(); }); });
  // ---- 며칠 칩 — 날짜 칩과 같은 규칙(건수 표시 · 0곳 비활성) ----
  var nightEls = document.querySelectorAll(".fchip.nights");
  function syncNightChips() {
    for (var k = 0; k < nightEls.length; k++) {
      var el = nightEls[k], m = el.getAttribute("data-nights"), cnt = el.querySelector("i");
      if (!m) continue;                                        // 상관없어는 건수를 안 센다
      var n = 0;
      for (var i = 0; i < CITY.length; i++) if (matchesNights(CITY[i], m)) n++;
      if (cnt) cnt.textContent = n + "곳";
      el.disabled = (n === 0 && nightsMode !== m);
      el.classList.toggle("empty", n === 0);
    }
  }
  for (var ni = 0; ni < nightEls.length; ni++) (function (el) {
    el.addEventListener("click", function () {
      if (el.disabled) return;
      nightsMode = el.getAttribute("data-nights");
      for (var k = 0; k < nightEls.length; k++) nightEls[k].classList.toggle("on", nightEls[k].getAttribute("data-nights") === nightsMode);
      applyFilter();
    });
  })(nightEls[ni]);
  var moodEls = document.querySelectorAll(".fchip.moodf");
  for (var mi = 0; mi < moodEls.length; mi++) (function (el) { el.addEventListener("click", function () { if (el.disabled) return; var m = el.dataset.mood; mood = (mood === m ? null : m); for (var k = 0; k < moodEls.length; k++) moodEls[k].classList.toggle("on", moodEls[k].dataset.mood === mood); applyFilter(); }); })(moodEls[mi]);
  function syncMoodChips() {
    for (var k = 0; k < moodEls.length; k++) {
      var el = moodEls[k], m = el.getAttribute("data-mood"), cnt = el.querySelector("i"), n = 0;
      for (var i = 0; i < CITY.length; i++) if (CITY[i].tags.indexOf(m) >= 0) n++;
      if (cnt) cnt.textContent = n + "곳";
      el.disabled = (n === 0 && mood !== m);
      el.classList.toggle("empty", n === 0);
    }
  }
  if (bslider) bslider.addEventListener("input", function () { budget = +bslider.value; if (bval) bval.textContent = budgetLabel(); applyFilter(); });
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
    resetBudget();          // 출발지가 바뀌면 딜이 통째로 바뀌므로 예산 범위도 새로 잡는다
    var pill = document.getElementById("originPill"); if (pill) pill.textContent = o.name + " 출발 ▾";
    document.getElementById("intro").classList.add("hide");
    stageIdx = 0; expandedI = null; active = null; render();
    // 화면0 → 지도: "지도가 스르륵 열린다". 근거리보다 더 당긴 자리에서 줌아웃한다.
    if (CURV && !reduceMotion()) tweenTo({ lon: CURV.lon, lat: CURV.lat, scale: CURV.scale * 2.6 }, CURV, 600);
  }
  var pill0 = document.getElementById("originPill");
  if (pill0) pill0.addEventListener("click", function () { document.getElementById("intro").classList.remove("hide"); });

  renderIntro();
})();
