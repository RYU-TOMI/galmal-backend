# -*- coding: utf-8 -*-
"""갈래말래 화면 빌드 — v1 응답을 받아 정적 HTML 을 굽는다.

    python site/build.py --api fixtures/v1          # 로컬 사본으로 (네트워크 없이)
    python site/build.py --api https://api.galmal.kr/v1
    python site/build.py --api fixtures/v1 --out /tmp/out --only ICN-FUK

**분리 후 프론트 저장소의 유일한 진입점이다.** 지금은 `collector/build_site.py` 와
나란히 존재하고 크론은 아직 옛 것을 부른다 — 스위치는 M3 다.

## 이게 「API 를 쓰는 프론트」인가

아니다. **빌드 타임에** 한 번 받아서 HTML 에 박아 넣는다(SSG). 방문자 브라우저는
아무것도 요청하지 않는다. 그래서 CORS·로딩 상태·재시도·레이트리밋이 전부 없다.
`--api` 가 URL 이든 폴더든 같은 일을 하는 것도 그래서다.

바뀌는 건 **경계**다 — 프론트가 sqlite 를 직접 열던 것이 계약을 읽는 것으로 바뀐다.
나중에 백엔드가 자체 서버가 되면 **이 인자에 넣는 문자열만 바뀐다.**
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import route  # noqa: E402  (위 sys.path 설정 뒤여야 한다)
import seo    # noqa: E402


def main():
    ap = argparse.ArgumentParser(description="v1 응답에서 화면을 굽는다")
    ap.add_argument("--api", required=True,
                    help="v1 base — URL(https://api.galmal.kr/v1) 또는 폴더(fixtures/v1)")
    ap.add_argument("--out", default="docs",
                    help="산출물 폴더 (기본 docs)")
    ap.add_argument("--only", default=None,
                    help="노선 코드 하나만 굽는다 (예: ICN-FUK). 대조할 때 쓴다")
    a = ap.parse_args()

    pages = route.build_all(a.api)
    if a.only:
        want = a.only + ".html"
        pages = {k: v for k, v in pages.items() if k == want}
        if not pages:
            sys.exit("노선 %s 이 응답에 없다" % a.only)

    dst = os.path.join(a.out, "routes")
    os.makedirs(dst, exist_ok=True)
    for name, html_text in pages.items():
        with open(os.path.join(dst, name), "w", encoding="utf-8", newline="") as f:
            f.write(html_text)
    print("노선 페이지 %d장 → %s" % (len(pages), dst))

    # sitemap 은 전체 목록이라 `--only` 로 일부만 구웠으면 만들지 않는다 —
    # 반쪽짜리 sitemap 을 내보내는 것이 안 내보내는 것보다 나쁘다.
    if a.only:
        print("--only 라 sitemap·robots 는 건너뛴다")
        return
    meta = route.fetch(a.api, "meta.json")
    index = route.fetch(a.api, "routes/index.json")
    os.makedirs(a.out, exist_ok=True)
    for name, text in seo.build_all(index, meta["generated"][:10]).items():
        with open(os.path.join(a.out, name), "w", encoding="utf-8", newline="") as f:
            f.write(text)
        print("  %s" % name)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
