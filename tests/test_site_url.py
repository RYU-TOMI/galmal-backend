# -*- coding: utf-8 -*-
"""사이트 주소가 한 곳에서만 나오는가 (BE7).

도메인은 `canonical` · `og:url` · `sitemap.xml` · JSON-LD · 알림 메일이 전부
쓰는 값이다. 두 곳에 적혀 있으면 **바꾸는 날 한쪽만 바뀐다.**

실제로 그랬다. 2026-09-05 `galmal.kr` 전환 직전까지 `theme.BASE_URL`과
`send_alerts.SITE_URL`이 각자 옛 주소를 들고 있었다. `theme` 쪽만 고쳤다면
**화면은 전부 멀쩡하고 알림 메일만 옛 주소를 가리켰을 것이다** — 화면을 아무리
봐도 안 보이는 종류다.

이 프로젝트가 반복해 만난 그 유형이다(`timeutil` · `labels.city()` ·
`labels.REGION` · 빵부스러기 문자열 · 차트 안내 문구).
"""
import re
import unittest
from pathlib import Path

import theme

ROOT = Path(__file__).resolve().parent.parent
COLLECTOR = ROOT / "collector"
DOCS = ROOT / "docs"

# 절대 URL로 보이는 우리 사이트 주소. 폰트 CDN 같은 남의 도메인은 대상이 아니다.
SITE_DOMAIN_RE = re.compile(r"https?://(?:[\w-]+\.)*(?:github\.io|galmal\.kr)")

# 도메인을 알아도 되는 유일한 모듈. 여기가 정본이다.
OWNER = "theme.py"


class SingleSourceTest(unittest.TestCase):

    def test_only_theme_hardcodes_the_domain(self):
        """다른 모듈이 주소를 다시 적으면 실패한다.

        **테스트도 검사 대상이다.** 전환하던 날 `test_route_pages.py`가
        `"promo-ticket-site/"`를 하드코딩하고 있어서 36개가 한꺼번에 깨졌다 —
        도메인 하드코딩을 없애는 작업에서 하드코딩이 발목을 잡았다.
        """
        offenders = []
        scanned = list(COLLECTOR.glob("*.py")) + list((ROOT / "tests").glob("*.py"))
        for f in sorted(scanned):
            if f.name in (OWNER, Path(__file__).name):
                continue
            for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
                if SITE_DOMAIN_RE.search(line) and not line.lstrip().startswith("#"):
                    offenders.append(f"{f.name}:{i}")
        self.assertEqual(
            offenders, [],
            f"도메인은 theme.BASE_URL이 정본이다 — 직접 적은 곳: {offenders}")

    def test_alert_mail_derives_from_theme(self):
        """알림 메일 주소가 정본에서 파생되는가 — 갈라졌던 바로 그 자리."""
        import send_alerts
        self.assertTrue(send_alerts.SITE_URL.startswith(theme.BASE_URL))

    def test_base_url_shape(self):
        """끝에 슬래시가 붙으면 `BASE_URL + "/routes/..."`가 `//`가 된다."""
        self.assertTrue(theme.BASE_URL.startswith("https://"))
        self.assertFalse(theme.BASE_URL.endswith("/"))


class DeployedArtifactTest(unittest.TestCase):
    """커밋된 산출물이 전부 같은 주소를 쓰는가.

    재빌드를 잊은 채 코드만 고치면 여기서 걸린다 — 배포되는 건 파일이다.
    """

    @classmethod
    def setUpClass(cls):
        cls.sitemap = DOCS / "sitemap.xml"
        cls.robots = DOCS / "robots.txt"
        cls.routes = sorted((DOCS / "routes").glob("*.html"))
        if not cls.routes:
            raise unittest.SkipTest("노선 페이지가 아직 생성되지 않았다")

    def stale(self, text):
        """정본이 아닌 우리 도메인이 남아 있으면 그 목록."""
        return sorted({m for m in SITE_DOMAIN_RE.findall(text)
                       if m != theme.BASE_URL})

    def test_sitemap_uses_the_canonical_domain(self):
        self.assertEqual(self.stale(self.sitemap.read_text(encoding="utf-8")), [])

    def test_robots_points_at_the_canonical_sitemap(self):
        text = self.robots.read_text(encoding="utf-8")
        self.assertIn(f"{theme.BASE_URL}/sitemap.xml", text)
        self.assertEqual(self.stale(text), [])

    def test_route_pages_use_the_canonical_domain(self):
        """canonical · og:url · og:image · JSON-LD가 전부 여기서 파생된다."""
        for p in self.routes:
            with self.subTest(page=p.name):
                self.assertEqual(self.stale(p.read_text(encoding="utf-8")), [])

    def test_cname_matches_the_base_url(self):
        """`docs/CNAME`이 `BASE_URL`과 다르면 도메인이 조용히 풀린다.

        GitHub Pages 설정이 이 파일을 만든다. 크론이 `docs/`를 매일 재생성하므로,
        파일이 사라지거나 어긋나면 **사이트가 죽는 게 아니라 404가 된다.**
        """
        cname = DOCS / "CNAME"
        self.assertTrue(cname.exists(), "docs/CNAME이 사라졌다 — 커스텀 도메인이 풀린다")
        host = cname.read_text(encoding="utf-8").strip()
        self.assertEqual(f"https://{host}", theme.BASE_URL)


if __name__ == "__main__":
    unittest.main()
