/* 갈래말래 발견 지도 — d3-geo(투영·경로)만 사용, DOM/이벤트는 순수 JS.
   파트1: 세계 윤곽 + 한국 확대 화면 + 출발 공항 5개 원. (상호작용은 이후 파트) */
(function () {
  "use strict";
  var SVGNS = "http://www.w3.org/2000/svg";
  var W = 800, H = 600, PAD = 24;

  var svg = document.getElementById("map");
  if (!svg || !window.d3 || !d3.geoEquirectangular) return;

  var proj = d3.geoEquirectangular();
  var path = d3.geoPath(proj);

  // 뷰 정의: [서, 동, 남, 북] 경위도 박스. 파트1은 korea 뷰만 사용.
  var VIEWS = {
    korea: [120, 136, 30, 43],
    asia: [95, 150, -5, 48],
    world: [-20, 200, -50, 70]
  };

  function bbox(v) {
    var w = v[0], e = v[1], s = v[2], n = v[3];
    return { type: "Feature", geometry: { type: "Polygon",
      coordinates: [[[w, s], [e, s], [e, n], [w, n], [w, s]]] } };
  }
  function fitView(name) {
    proj.fitExtent([[PAD, PAD], [W - PAD, H - PAD]], bbox(VIEWS[name]));
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
