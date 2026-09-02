# -*- coding: utf-8 -*-
"""노선 페이지의 구조화 데이터 — 화면에 없는 걸 마크업하지 않는가 (BE4 T3).

구조화 데이터는 **검색엔진에만 보이는 주장**이다. 화면과 어긋나면 사용자는
영영 모르고 우리도 모른다 — 구글이 스팸으로 판정할 때까지는. 그래서 눈으로
확인할 수 없는 종류이고, 자동 검사의 값어치가 크다.

여기서 지키는 건 하나다: **JSON-LD가 말하는 것과 페이지가 보여주는 것이 같다.**

커밋된 산출물(`docs/routes/*.html`)을 읽는다. 빌드를 다시 돌리지 않으므로
"실제로 배포되는 파일"을 검사하는 셈이고, 재빌드를 잊은 채 코드만 고친 경우도
여기서 걸린다.
"""
import json
import re
import unittest
from datetime import date
from pathlib import Path

ROUTES_DIR = Path(__file__).resolve().parent.parent / "docs" / "routes"
JSONLD_RE = re.compile(
    r'<script type="application/ld\+json">(.*?)</script>', re.S)
CRUMB_RE = re.compile(r'<p class="crumb">(.*?)</p>', re.S)
TAG_RE = re.compile(r"<[^>]+>")

# 쓰면 안 되는 스키마. 우리는 항공권을 **팔지 않는다** — 남의 가격을 보여주고
# 예약처로 넘길 뿐이다. 파는 척하는 마크업은 사실과 다르고 스팸 판정 대상이다.
FORBIDDEN_TYPES = {"Product", "Offer", "AggregateOffer",
                   "FlightReservation", "Flight"}


def route_pages():
    return sorted(ROUTES_DIR.glob("*.html"))


def structured(html):
    """페이지의 JSON-LD 덩이들을 평평한 리스트로."""
    out = []
    for raw in JSONLD_RE.findall(html):
        parsed = json.loads(raw.replace("<\\/", "</"))
        out.extend(parsed if isinstance(parsed, list) else [parsed])
    return out


def visible_crumb(html):
    """화면의 `특가 피드 › 일본 › 인천 → 도쿄`를 단계 목록으로."""
    m = CRUMB_RE.search(html)
    if not m:
        return None
    text = TAG_RE.sub("", m.group(1))
    return [part.strip() for part in text.split("›")]


class RoutePageStructuredDataTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.pages = {p.name: p.read_text(encoding="utf-8") for p in route_pages()}
        if not cls.pages:
            raise unittest.SkipTest("노선 페이지가 아직 생성되지 않았다")

    def blocks(self, html, type_):
        return [b for b in structured(html) if b.get("@type") == type_]

    def test_every_page_has_parsable_structured_data(self):
        """깨진 JSON-LD는 **조용히 무시된다** — 넣어놓고 안 먹는 줄 모른다."""
        for name, html in self.pages.items():
            with self.subTest(page=name):
                blocks = structured(html)
                self.assertTrue(blocks, "JSON-LD가 없다")
                for b in blocks:
                    self.assertEqual(b.get("@context"), "https://schema.org")

    def test_breadcrumb_matches_what_the_page_shows(self):
        """이 파일의 존재 이유. 마크업이 화면보다 많거나 적으면 실패한다."""
        for name, html in self.pages.items():
            with self.subTest(page=name):
                shown = visible_crumb(html)
                self.assertIsNotNone(shown, "화면에 브레드크럼이 없다")
                crumbs = self.blocks(html, "BreadcrumbList")
                self.assertEqual(len(crumbs), 1)
                marked = [item["name"]
                          for item in crumbs[0]["itemListElement"]]
                self.assertEqual(marked, shown,
                                 f"{name}: 마크업 {marked} != 화면 {shown}")

    def test_breadcrumb_positions_are_sequential(self):
        for name, html in self.pages.items():
            with self.subTest(page=name):
                items = self.blocks(html, "BreadcrumbList")[0]["itemListElement"]
                self.assertEqual([i["position"] for i in items],
                                 list(range(1, len(items) + 1)))

    def test_breadcrumb_links_only_to_pages_that_exist(self):
        """없는 URL을 지어내면 크롤러가 404를 먹는다 — `route` 필드와 같은 교훈."""
        docs = ROUTES_DIR.parent
        for name, html in self.pages.items():
            with self.subTest(page=name):
                for item in self.blocks(html, "BreadcrumbList")[0]["itemListElement"]:
                    href = item.get("item")
                    if not href:
                        continue        # 링크 없는 단계는 정상(지역·현재 페이지)
                    rel = href.split("promo-ticket-site/", 1)[-1] or "index.html"
                    target = docs / (rel if rel else "index.html")
                    if target.is_dir() or not rel:
                        target = docs / "index.html"
                    self.assertTrue(target.exists(), f"{href} → 파일 없음")

    def test_webpage_url_is_the_canonical_url(self):
        """JSON-LD의 url과 <link rel=canonical>이 다르면 어느 쪽이 진짜인지 모른다."""
        for name, html in self.pages.items():
            with self.subTest(page=name):
                wp = self.blocks(html, "WebPage")
                self.assertEqual(len(wp), 1)
                m = re.search(r'<link rel="canonical" href="([^"]+)"', html)
                self.assertEqual(wp[0]["url"], m.group(1))

    def test_date_modified_is_an_iso_date(self):
        """매일 갱신을 주장하는 값이라 형식이 깨지면 신선도 신호가 죽는다."""
        for name, html in self.pages.items():
            with self.subTest(page=name):
                raw = self.blocks(html, "WebPage")[0]["dateModified"]
                date.fromisoformat(raw)      # 형식이 아니면 예외

    def test_no_schema_that_claims_we_sell_tickets(self):
        """우리는 항공권을 팔지 않는다. 파는 척하는 마크업은 사실과 다르다."""
        for name, html in self.pages.items():
            with self.subTest(page=name):
                used = {b.get("@type") for b in structured(html)}
                self.assertEqual(used & FORBIDDEN_TYPES, set(),
                                 f"{name}: 쓰면 안 되는 스키마 {used & FORBIDDEN_TYPES}")

    def test_script_tag_cannot_be_broken_out_of(self):
        """값에 `</script>`가 섞이면 페이지가 거기서 끊긴다."""
        for name, html in self.pages.items():
            with self.subTest(page=name):
                for raw in JSONLD_RE.findall(html):
                    self.assertNotIn("</script>", raw)


if __name__ == "__main__":
    unittest.main()
