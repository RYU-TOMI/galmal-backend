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
- **하루 두 번 예약**: `14:10 UTC`(23:10 KST) 주 실행 · `18:10 UTC`(03:10 KST) 예비. 끝나면 프론트에 `repository_dispatch`(`client_payload.generated`).
  - **예비는 오늘 발행이 이미 있으면 즉시 끝난다**(「오늘 발행 확인」 스텝이 `meta.generated`를 본다). 주 실행이 큐에서 버려졌거나 발행까지 못 간 날에만 일한다.
  - **UTC 자정에서 멀어야 한다** — `fetched_date`가 UTC 날짜라 자정에 걸치면 수집일에 구멍이 난다(BB36). 지연은 우리가 못 줄인다(GitHub 큐) — **여유로 견딘다.**
  - 손으로 돌리면(`workflow_dispatch`) **가드와 무관하게 언제나 돈다.**
- **손으로 돌릴 땐 `workflow_dispatch`의 `skip_side_effects=true`** — 메일 수집·파싱·알림 발송을 건너뛴다. `mail_ingest`는 메일을 소비하므로(BB33) 검증 실행에서 켜 두면 안 된다.
- 시크릿은 **`production` 환경**에만 있다. 변수 `API_URL`·`SITE_URL`은 로그에 보여야 해서 vars다.
- 마지막 「상태 점검」이 API 신선도·사이트 `build.json` 일치·구독 주소를 본다. **「못 받음」은 실패다.**

## 이 저장소는 공개다 — 숫자를 적기 전에
- 🔴 **유입·전환 수치는 저장소에 적지 않는다 — 파일도, 문서 본문도.** 서치콘솔 노출·클릭·평균 순위, 방문자 수, 전환율이 그렇다.
  **판단과 원인만 적고 숫자는 노션에 둔다**(`SESSIONS.md` §법적·보안의 「매출·전환 수치는 노션에」).
  2026-09-21에 SEO 실측 수치를 `BACKEND.md`에 그대로 적었다가 내렸다 — **「CSV는 저장소에 안 넣었다」면서 본문에 옮겨 적으면 같은 일이다.**
- 수집·발행 수치(딜 건수·노선 수·표본 수)는 **API가 이미 공개하므로** 적어도 된다. 가르는 기준은 **「우리에게 사람이 얼마나 오는가」인지**다.

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
