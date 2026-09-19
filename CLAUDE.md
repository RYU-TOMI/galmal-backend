# galmal-backend — 백엔드 세션

@../galmal-plan/SESSIONS.md

> 위 한 줄이 **세 세션 공통 규칙**을 가져온다(형제 폴더 `../galmal-plan/`). 가져오기가 안 되면 그 파일을 **먼저 직접 읽는다.**
> 이 파일에는 **이 저장소만의 규칙**을 둔다. 작업 방식·챕터·곁가지 백로그는 `BACKEND.md`.

## 이 저장소

수집(가격·광역·메일) · 특가 판정 · **v1 API 발행** · 구독 알림 · 크론. **계약 정본**(`contract/v1/`)을 갖는다.
발행물은 `docs/v1/` → GitHub Pages → **`https://api.galmal.kr/v1/`**. 화면(HTML)은 만들지 않는다 — 프론트 저장소가 만든다.

| 경로 | 무엇 |
|---|---|
| `collector/` | 수집기·판정·발행. 진입점 **`collector/publish.py`** |
| `contract/v1/` | **계약 정본** — `deal.schema.json`(필드·타입·nullable·의미) · `vocab.json`(태그·when·region·haul·tier·hub) |
| `collector/dests.py` | 도시별 태그 배정 `DEST` · 지역 표시명 `REGION_NAME`의 정본 |
| `docs/v1/` | 발행물(크론이 커밋) |
| `data/` | `prices.db` 등 수집 누적(크론이 커밋) |

## 계약
- **기획 결정 없이 `contract/`를 바꾸지 않는다.** 바꿀 땐 커밋 메시지에 그 결정(`DECISIONS.md` 날짜)을 인용한다.
- `DEST`의 태그 **배열 순서는 편집 판단이다 — 정렬하지 않는다.** 상위 태그 중 첫째가 카드의 대표 태그다(`galmal-plan/TAGS.md` §배정).
- **한 발행의 모든 응답은 같은 `generated`**, 단 딜 보존일(`meta.preserved=true`)엔 `deals`만 더 이르다(`galmal-plan/CONTRACT.md` §공통 규칙, 테스트가 잠근다).

## 크론 (`.github/workflows/collect.yml`)
- 매일 `22:10 UTC` 예약(GitHub 지연으로 실제 시작은 ~2시간 늦을 수 있다). 끝나면 프론트에 `repository_dispatch`(`client_payload.generated`).
- **손으로 돌릴 땐 `workflow_dispatch`의 `skip_side_effects=true`** — 메일 수집·파싱·알림 발송을 건너뛴다. `mail_ingest`는 메일을 소비하므로(BB33) 검증 실행에서 켜 두면 안 된다.
- 시크릿은 **`production` 환경**에만 있다. 변수 `API_URL`·`SITE_URL`은 로그에 보여야 해서 vars다.
- 마지막 「상태 점검」이 API 신선도·사이트 `build.json` 일치·구독 주소를 본다. **「못 받음」은 실패다.**

## git
- `main`에 **크론이 매일 `data/`·`docs/v1/`를 커밋**한다 → **push 전 반드시 pull.**
- 충돌 시 생성물은 **원격 것을 이름으로 집는다**: `git checkout origin/main -- docs/v1 data/prices.db data/deals_latest.txt`
  > ⚠️ `--theirs`를 쓰지 않는다 — merge와 rebase에서 가리키는 쪽이 반대다.
- 🔴 **재빌드는 `.env`가 있는 환경에서만.** 시크릿 없이 돌리면 제휴 링크가 **경고 없이** 빠진다(BB30). 재빌드했으면 커밋 전:
  ```bash
  python -c "import json; d=json.load(open('docs/v1/deals.json',encoding='utf-8')); print(len(d['deals']), sum(any(l.get('ad') for l in x['links']) for x in d['deals']))"
  # 두 숫자가 같으면 정상. 건수를 기대값으로 적지 않는다(매일 바뀐다). grep -c 도 쓰지 않는다(한 줄 파일이라 항상 1).
  ```
- 테스트: `python -m unittest discover -s tests -t . -v` — **출력에서 `^OK`를 확인**하고 커밋한다.
