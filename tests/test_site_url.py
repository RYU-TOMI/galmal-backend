# -*- coding: utf-8 -*-
"""백엔드가 사이트 주소를 **하드코딩하지 않는가** (M3 T4 · P2).

도메인은 `canonical` · `og:url` · `sitemap.xml` · JSON-LD · 알림 메일이 전부 쓰는 값이다.
두 곳에 적혀 있으면 **바꾸는 날 한쪽만 바뀐다.**

실제로 그랬다. 2026-09-05 `galmal.kr` 전환 직전까지 `theme.BASE_URL`과
`send_alerts.SITE_URL`이 각자 옛 주소를 들고 있었다. 한쪽만 고쳤다면 **화면은 전부
멀쩡하고 알림 메일만 옛 주소를 가리켰을 것이다** — 화면을 아무리 봐도 안 보이는 종류다.

## M3 T4에서 바뀐 것

`theme.py`가 프론트로 갔다. 그래서 **정본이 백엔드에 없다** — 주소를 아는 유일한
백엔드 모듈은 `send_alerts`이고(메일이 사이트로 링크한다), 그 값은 **배포 설정
(`vars.SITE_URL`)에서 온다.**

이 파일이 지키는 건 하나로 좁혀졌다: **백엔드 코드 어디에도 우리 도메인이 적혀 있지 않다.**
예전엔 `theme.py` 하나를 예외로 뒀는데, 이제 **예외가 없다.**

> 화면 산출물(`sitemap.xml`·`robots.txt`·노선 HTML)이 같은 도메인을 쓰는지,
> `docs/CNAME`이 맞는지는 **프론트가 만드는 것**이라 프론트 몫으로 넘겼다.
> 백엔드 테스트가 남의 산출물을 검사하면, 그쪽이 고칠 때 우리 테스트가 깨진다.
"""
import os
import re
import unittest
from unittest import mock
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COLLECTOR = ROOT / "collector"

# 절대 URL로 보이는 우리 사이트 주소. 폰트 CDN 같은 남의 도메인은 대상이 아니다.
SITE_DOMAIN_RE = re.compile(r"https?://(?:[\w-]+\.)*(?:github\.io|galmal\.kr)")


class NoHardcodedDomainTest(unittest.TestCase):

    def test_no_backend_file_hardcodes_the_domain(self):
        """🔴 예외가 없다 — `theme.py`가 사라졌으므로 정본도 백엔드에 없다.

        **테스트도 검사 대상이다.** 2026-09-05 전환하던 날 `test_route_pages.py`가
        `"promo-ticket-site/"`를 하드코딩하고 있어서 36개가 한꺼번에 깨졌다 —
        도메인 하드코딩을 없애는 작업에서 하드코딩이 발목을 잡았다.
        """
        offenders = []
        scanned = list(COLLECTOR.glob("*.py")) + list((ROOT / "tests").glob("*.py"))
        for f in sorted(scanned):
            if f.name == Path(__file__).name:      # 이 파일의 정규식은 제외
                continue
            for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
                if SITE_DOMAIN_RE.search(line) and not line.lstrip().startswith("#"):
                    offenders.append(f"{f.name}:{i}")
        self.assertEqual(
            offenders, [],
            "백엔드는 도메인을 모른다 — 배포 설정(vars.SITE_URL)에서 받는다. "
            f"직접 적은 곳: {offenders}")


class AlertMailSiteUrlTest(unittest.TestCase):
    """알림 메일이 주소를 **환경에서** 받는가, 그리고 없으면 멈추는가."""

    def reload(self, value):
        """`SITE_URL`을 주고 모듈을 다시 읽는다 — 상수라 import 시점에 정해진다."""
        import importlib
        import send_alerts
        with mock.patch.dict(os.environ, {"SITE_URL": value}, clear=False):
            return importlib.reload(send_alerts)

    def tearDown(self):
        self.reload("https://galmal.kr")           # 다른 테스트에 새지 않게 되돌린다

    def test_it_comes_from_the_environment(self):
        self.assertEqual(self.reload("https://example.test").SITE_URL,
                         "https://example.test/")

    def test_trailing_slash_is_normalised(self):
        """설정값에 `/`가 붙어 와도 링크가 `//`가 되지 않는다."""
        self.assertEqual(self.reload("https://example.test/").SITE_URL,
                         "https://example.test/")

    def test_whitespace_is_stripped(self):
        """🔴 복붙하면 값 끝에 `\\r\\n`이 딸려 온다 — 2026-09-15에 실제로 그랬다.

        그대로 두면 메일 링크가 `https://example.test⏎/` 가 된다.
        """
        self.assertEqual(self.reload(" https://example.test\r\n").SITE_URL,
                         "https://example.test/")

    def test_empty_stops_before_sending(self):
        """주소 없이 보내면 **어디로도 안 가는 링크**가 든 메일이 나간다.

        받는 사람은 링크가 죽었다고만 느끼고 우리는 보냈다고 믿는다 — 조용한 실패다.
        """
        mod = self.reload("")
        with self.assertRaises(SystemExit):
            mod.require_site_url()


if __name__ == "__main__":
    unittest.main()
