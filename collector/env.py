# -*- coding: utf-8 -*-
"""`.env`와 환경변수를 읽는 **한 곳** (BB41, BE18).

같은 파싱이 다섯 벌 있었다 — `fetch_prices`·`fetch_breadth`·`parse_mail`의 `load_*`,
`mail_ingest.load_env`, `affiliates._env`. 전부 「환경변수 우선, 없으면 `.env`」였지만
미묘하게 달랐다(주석 처리 · 중복 키 · 캐시 유무). **같은 사실을 다섯 곳에 두면 하루는 하나가 틀린다** —
이 저장소는 `CONTRACT.md` 사본·구독 본문 사본·지역 어휘로 이미 세 번 겪었다.

규칙 두 가지:
  1. **환경변수가 이긴다.** 크론(Actions)은 시크릿을 환경변수로 넣고 `.env`가 없다.
     로컬은 `.env`로 산다. 둘 다 있으면 환경변수다 — 손으로 덮어쓸 수 있어야 한다.
  2. **빈 값은 없는 것과 같다.** `SITE_URL=` 처럼 이름만 있는 줄, 빈 환경변수 모두 `None`.
     예전 다섯 벌이 전부 `if val:`로 그렇게 다뤘고, 그 덕에 「빈 문자열이 시크릿 행세를 하는」 일이 없었다.

🔴 **여기서 값을 로그에 찍지 않는다.** 시크릿이 지나가는 유일한 길목이다.
"""
import os
from pathlib import Path

ENV_FILE = Path(__file__).resolve().parent.parent / ".env"

# 파일 내용 캐시. 키에 mtime·크기를 넣어 **파일이 바뀌면 저절로 무효**가 된다.
# 예전 `affiliates._env`는 호출마다 파일을 다시 읽었다 — 딜 한 건의 링크를 만들 때마다 여러 번이다.
_cache = {}


def _file_values(path=None):
    """`.env`를 `{키: 값}`으로. 없거나 못 읽으면 `{}`.

    **같은 키가 두 번 있으면 먼저 나온 줄이 이긴다**(`setdefault`). 예전 구현들이
    `startswith(f"{name}=")`로 **첫 매치**를 가져갔으므로 그 동작을 그대로 옮긴 것이다.
    """
    path = path or ENV_FILE
    try:
        st = path.stat()
    except OSError:
        return {}
    key = (str(path), st.st_mtime_ns, st.st_size)
    if key not in _cache:
        _cache.clear()                      # 경로가 바뀌면 옛 것을 들고 있지 않는다
        values = {}
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            values.setdefault(k.strip(), v.strip())
        _cache[key] = values
    return _cache[key]


def get(name, path=None):
    """환경변수 → `.env` 순으로 찾은 값. 없거나 비었으면 `None`."""
    val = os.environ.get(name)
    if val and val.strip():
        return val.strip()
    val = _file_values(path).get(name)
    return val or None


def require(name, hint="`.env` 파일 또는 환경변수로 설정하세요."):
    """없으면 **종료 코드 1로 멈춘다.** 조용히 빈 값으로 계속 가지 않는다.

    시크릿이 빠진 채 도는 건 이 저장소가 가장 비싸게 배운 실패다(BB30 — 마커 없이 빌드하면
    사이트는 멀쩡하고 수익 링크만 사라진다). 수집 토큰도 같다: 없으면 그 자리에서 멈춰야
    빈 산출물이 배포되지 않는다.
    """
    val = get(name)
    if not val:
        raise SystemExit(f"{name}이(가) 없습니다. {hint}")
    return val
