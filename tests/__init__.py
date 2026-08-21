# -*- coding: utf-8 -*-
"""백엔드 테스트 패키지.

`collector/*.py`는 서로를 `import dests` 처럼 형제 모듈로 부른다. 실행 진입점
(`fetch_prices.py` 등)은 각자 `sys.path.insert`로 이를 해결하지만
`discover_data.py`·`dests.py`는 그러지 않으므로, 저장소 루트에서 그냥
import하면 실패한다. 여기서 한 번만 경로를 넣어 준다.

실행:
    python -m unittest discover -s tests -t . -v

`-t .`(최상위 = 저장소 루트)를 붙여야 `tests`가 패키지로 로드되어 이 파일이
테스트보다 먼저 실행된다. 생략하면 경로 설정이 안 돼 import 에러가 난다.

원칙: 테스트는 실 DB(`data/prices.db`)와 네트워크를 건드리지 않는다.
DB가 필요하면 `sqlite3.connect(":memory:")` + `db.SCHEMA`를 쓴다.
"""
import sys
from pathlib import Path

_COLLECTOR = Path(__file__).resolve().parent.parent / "collector"
if str(_COLLECTOR) not in sys.path:
    sys.path.insert(0, str(_COLLECTOR))
