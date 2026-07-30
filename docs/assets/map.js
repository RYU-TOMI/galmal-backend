/* 갈래말래 발견 지도 — d3-geo(투영·경로)만 사용, DOM/이벤트는 순수 JS.
   파트1: 세계 윤곽 + 한국 확대 화면 + 출발 공항 5개 원. (상호작용은 이후 파트) */
(function () {
  "use strict";
  var SVGNS = "http://www.w3.org/2000/svg";
  var W = 800, H = 600, PAD = 24;

  var svg = document.getElementById("map");
  if (!svg || !window.d3 || !d3.geoEquirectangular) return;

  var proj = d3.geoEquirectangular().translate([W / 2, H / 2]);
  var path = d3.geoPath(proj);

  // 뷰 정의: 중심 경도(rotate)·중심 위도(center)·배율(scale). 명시적 파라미터로 확정.
  var VIEWS = {
    korea: { lon: 127.5, lat: 36.5, scale: 2400 },   // 한국 확대
    asia: { lon: 122, lat: 22, scale: 620 },          // 일본~동남아
    world: { lon: 60, lat: 25, scale: 150 }           // 전 세계
  };

  function fitView(name) {
    var v = VIEWS[name];
    proj.rotate([-v.lon, 0]).center([0, v.lat]).scale(v.scale).translate([W / 2, H / 2]);
  }
  function el(tag, attrs) {
    var e = document.createElementNS(SVGNS, tag);
    for (var k in attrs) e.setAttribute(k, attrs[k]);
    return e;
  }
  function group(id) {
    var g = el("g", { id: id });
    svg.appendChild(g);
    return g;
  }

  fetch("data/world.geojson").then(function (r) { return r.json(); }).then(function (world) {
    fitView("korea");

    // 육지
    var gLand = group("land");
    gLand.appendChild(el("path", { d: path(world), class: "land" }));

    // 출발 공항
    var gAir = group("airports");
    (window.__ORIGINS || []).forEach(function (o) {
      var p = proj([o.lon, o.lat]);
      if (!p) return;
      var a = el("g", { class: "airport", "data-iata": o.iata });
      a.appendChild(el("circle", { cx: p[0], cy: p[1], r: 9, class: "air-dot" }));
      var t = el("text", { x: p[0], y: p[1] - 14, "text-anchor": "middle", class: "air-label" });
      t.textContent = o.name;
      a.appendChild(t);
      gAir.appendChild(a);
    });
  }).catch(function (err) {
    var t = el("text", { x: W / 2, y: H / 2, "text-anchor": "middle", class: "air-label" });
    t.textContent = "지도를 불러오지 못했습니다";
    svg.appendChild(t);
  });
})();
