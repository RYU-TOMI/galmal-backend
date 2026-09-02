# -*- coding: utf-8 -*-
"""OG 이미지 — 카카오톡·슬랙 링크 미리보기용 1200×630.

백엔드 요청(2026-09-02): og:image가 없어 카톡에 링크를 붙이면 미리보기가 백지다.
한국에서 링크는 카톡으로 도니 유입에 직접 영향이 있다.

**노선별 동적 생성은 안 한다.** OG는 래스터여야 하는데 Pillow도 Node도 없고,
넣으면 `CLAUDE.md`의 "Node 빌드 금지 / 런타임 CDN 의존 0"과 부딪힌다.
정적 1장으로 간다 — 노선별로 다르진 않지만 백지보다 훨씬 낫다.

**헤드리스 크롬은 빌드 의존이 아니다.** 이 스크립트는 사람이 한 번 돌려 PNG를
만들고, 커밋되는 산출물은 PNG 하나다. 크론은 `build_site.py`만 부른다.

왜 로고+글자만 두지 않았나: DESIGN.md 원칙 4 — "개성은 폰트 장난이 아니라
크기 대비·색·**지도**에서 나온다." 미리보기 한 장으로 "발견 지도"임이 읽혀야 한다.

소유: 기획 세션. 산출물 design/og.html → design/og.png
"""
import json, io, os, sys, math, subprocess, shutil

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

D = json.load(io.open(os.path.join(BASE, "..", "docs", "data", "deals.json"), encoding="utf-8"))
W = json.load(io.open(os.path.join(BASE, "..", "docs", "data", "world.geojson"), encoding="utf-8"))
SEL = [d for d in D["deals"] if d["o"] == "SEL"]
ORG = D["origins"]["SEL"]

OW, OH = 1200, 630
# 지도는 오른쪽으로 흘려보낸다 — 왼쪽 절반은 글자 자리다.
LON0, LAT0 = 116.0, 10.0
K = 232.0
MX, MY = OW * 0.625, OH * 0.47


def px(lon, lat):
    dl = ((lon - LON0 + 180) % 360) - 180
    return (MX + math.radians(dl) * K, MY - math.radians(lat - LAT0) * K)


def path_d(geom):
    """경도를 이어서 편다(unwrap). 날짜변경선에서 끊고 Z로 닫으면
    해안선이 아니라 엉뚱한 삼각형이 채워진다 — region.html에서 겪은 버그다."""
    rings = []
    t = geom["type"]
    if t == "Polygon":
        rings = geom["coordinates"]
    elif t == "MultiPolygon":
        for poly in geom["coordinates"]:
            rings.extend(poly)
    out = []
    for ring in rings:
        if len(ring) < 3:
            continue
        pts, prev = [], None
        for lon, lat in ring:
            if prev is not None:
                while lon - prev > 180:
                    lon -= 360
                while lon - prev < -180:
                    lon += 360
            prev = lon
            pts.append(px(lon, lat))
        # 남극은 버린다. 링이 극을 한 바퀴 돌아 unwrap 경도폭이 387도가 되고,
        # Z로 닫을 때 360도를 건너뛰는 **가로줄**이 생긴다. 게다가 자기교차라
        # nonzero 채우기가 엉뚱한 가로 띠를 여러 개 만든다(실제로 그렇게 나왔다).
        # 화면 밖이고 딜도 없다.
        # 지구를 한 바퀴 감는 링을 버린다. 남극 해안선과 극지 부속 링이 그런데,
        # unwrap하면 경도폭이 360도가 되어 **화면을 가로지르는 납작한 띠**가 된다.
        # (실제 렌더에서 가로 흰 줄로 나왔다. 육지 이음매인 줄 알았는데 이거였다.)
        # 실재하는 최대 육지는 아프로유라시아 198도라 200도로 끊으면 안전하다.
        if (max(p[0] for p in pts) - min(p[0] for p in pts)) > 200 * 0.01745 * K:
            continue
        # 무대 근처에 아무것도 안 걸치면 버린다(파일 크기)
        if max(p[0] for p in pts) < -80 or min(p[0] for p in pts) > OW + 80:
            continue
        if max(p[1] for p in pts) < -80 or min(p[1] for p in pts) > OH + 80:
            continue
        out.append("M" + "L".join("%.1f,%.1f" % p for p in pts) + "Z")
    return " ".join(out)


paths = []
for f in W["features"]:
    g = f.get("geometry")
    if not g:
        continue
    d = path_d(g)
    if d:
        paths.append(d)

# 핀 — 가격 낮은 순으로 상위 28곳. 다 찍으면 오른쪽이 뭉갠다.
top = sorted(SEL, key=lambda x: x["price"])[:28]
pins = "".join('<circle cx="%.1f" cy="%.1f" r="%s"/>' % (px(d["lon"], d["lat"]) + (
    "7" if d.get("tier") == "major" else "4.5",)) for d in top)
ox, oy = px(ORG["lon"], ORG["lat"])

HTML = """<meta charset="utf-8">
<link rel="preconnect" href="https://cdn.jsdelivr.net">
<link rel="stylesheet"
 href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.css">
<style>
  *{margin:0;padding:0;box-sizing:border-box}
  html,body{width:%(W)dpx;height:%(H)dpx;overflow:hidden}
  body{background:#F4F8F7;position:relative;
    font-family:'Pretendard Variable',Pretendard,'Malgun Gothic',sans-serif;color:#20353A}
  svg.map{position:absolute;inset:0}
  /* OG는 브랜드 이미지지 정치 지도가 아니다 — 국경선은 채움과 같은 색으로 덮는다. */
  svg.map path{fill:#D3E7DD;stroke:#D3E7DD;stroke-width:.6;stroke-linejoin:round}
  svg.map circle{fill:#F2603F}
  /* 왼쪽은 글자 자리 — 지도를 배경으로 눕힌다 */
  /* 헤드리스 크롬이 큰 그라디언트를 타일로 합성하며 가로 줄무늬를 남긴다.
     폭을 절반으로 줄이고 dithering 여지를 없앤다. */
  .veil{display:none}
  .txt{position:absolute;left:82px;top:0;height:%(H)dpx;
    display:flex;flex-direction:column;justify-content:center;gap:0}
  .wm{font-size:112px;font-weight:900;letter-spacing:-.045em;line-height:1}
  .wm i{color:#F2603F;font-style:normal}
  .tl{font-size:47px;font-weight:800;letter-spacing:-.035em;margin-top:26px;color:#20353A}
  .sb{font-size:26px;font-weight:600;color:#5E7A7C;margin-top:16px;letter-spacing:-.02em}
  .rule{width:74px;height:7px;background:#F2603F;border-radius:99px;margin-top:34px}
</style>
<svg class="map" width="%(W)d" height="%(H)d">
  <g>%(PATHS)s
  <g>%(PINS)s</g></g>
  <circle cx="%(OX).1f" cy="%(OY).1f" r="17" fill="none" stroke="#33534F" stroke-width="2" opacity=".38"/>
  <circle cx="%(OX).1f" cy="%(OY).1f" r="8" fill="#33534F"/>
</svg>
<div class="veil"></div>
<div class="txt">
  <div class="wm">갈래<i>말래</i></div>
  <div class="tl">어디, 갈까?</div>
  <div class="sb">시간 남는데 싸게 다녀올 곳</div>
  <div class="rule"></div>
</div>
""" % {"W": OW, "H": OH,
       "PATHS": "".join('<path d="%s"/>' % d for d in paths),
       "PINS": pins, "OX": ox, "OY": oy, "VW": int(OW * 0.62)}

html_path = os.path.join(BASE, "og.html")
io.open(html_path, "w", encoding="utf-8").write(HTML)
print("og.html  %d KB" % (len(HTML) // 1024))
print("  육지 조각 %d · 핀 %d" % (len(paths), len(top)))

CHROME = next((p for p in [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    shutil.which("chrome") or "", shutil.which("chromium") or "",
] if p and os.path.exists(p)), None)

if not CHROME:
    print("  ⚠️ 크롬을 못 찾았다 — og.html을 브라우저로 열어 1200×630으로 저장할 것")
    sys.exit(0)

out = os.path.join(BASE, "og.png")
if os.path.exists(out):
    os.remove(out)
subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                "--force-device-scale-factor=1",
                "--screenshot=" + out, "--window-size=%d,%d" % (OW, OH),
                "--virtual-time-budget=6000",
                "file:///" + html_path.replace("\\", "/")],
               capture_output=True, timeout=90)
if os.path.exists(out):
    print("og.png   %d KB" % (os.path.getsize(out) // 1024))
else:
    print("  ⚠️ 스크린샷 실패 — og.html을 직접 저장할 것")
