# 레포 분리 이전 계획 (M0~M6)

> **이 문서는 임시다.** 이전이 끝나면(M6) 삭제한다. 결론은 `DECISIONS.md`에,
> 최종 구조는 `PROJECT.md`에, 계약은 `CONTRACT.md`에 남는다.
>
> 소유: 기획 세션. **프론트·백엔드 세션은 자기 단계의 태스크를 여기서 읽는다.**

## 왜 하나 (2026-09-08 사용자 결정)

지금은 한 저장소 안에서 **백엔드가 HTML을 짜고 프론트가 백엔드 모듈을 import 한다.**
규모가 커져 백엔드가 자체 서버를 갖는 시점이 오면, 이 엉킴은 그때 풀기 훨씬 비싸다.
**어느 정도 완성된 지금**, 기능이 아니라 경계를 정리한다.

설계 기준은 하나로 요약된다:

> **나중에 백엔드가 자체 서버가 됐을 때, 프론트 코드가 한 글자도 안 바뀌어야 한다.**

기각한 대안과 근거는 `DECISIONS.md` 2026-09-08 항목.

---

## 1. 목표 구조

```
galmal-api  (공개)                         galmal-web  (공개)
├ collector/         수집·판정·메일·알림    ├ site/
│  └ publish.py      ← 진입점              │   ├ shell.py   <head>·CSS·도메인·OG
├ data/prices.db                           │   ├ home.py    index.html
├ tests/             계약 검증             │   ├ route.py   routes/*.html (36)
└ .github/workflows/collect.yml            │   ├ seo.py     sitemap·robots
                                           │   └ build.py   ← 진입점
        ↓ 발행                             ├ assets/   discover.js|css, d3
   api.galmal.kr/v1/*.json                 ├ fixtures/ v1 응답 사본(로컬 개발용)
   (오늘은 GitHub Pages,                   └ .github/workflows/deploy.yml
    나중에 자체 서버 — DNS만 옮긴다)              ↓ 소비
                                              galmal.kr  (Pages, 도메인)

galmal-plan  (비공개)  ← promo-ticket-site를 rename
└ 기획 문서 13종 + design/ 목업.  두 레포가 `../galmal-plan/`으로 참조한다.
```

**문서는 복사하지 않는다.** 두 벌이 되면 갈라지고, 갈라지면 2026-09-01 사고
(개명한 명칭이 전달되지 않아 구명칭이 검색엔진까지 나간 것)가 재발한다.
각 레포의 `CLAUDE.md`가 `../galmal-plan/<문서>.md`를 가리키고 원본은 한 벌만 둔다.

---

## 2. 설계 원칙 — 경계 판정 기준

애매한 코드가 나오면 이 여섯으로 판정한다.

| # | 원칙 | 위반의 냄새 |
|---|---|---|
| **P1** | **백엔드는 HTML을 만들지 않는다.** 태그 한 글자도. | 백엔드 파일에 `<div` |
| **P2** | **백엔드는 사이트 주소를 모른다.** `BASE_URL`·`SITE_NAME`·`OG_IMAGE`·소유확인 메타는 전부 프론트. | 백엔드가 `https://galmal.kr` |
| **P3** | **프론트는 DB를 모른다.** | 프론트 파일에 `sqlite3` / `conn` |
| **P4** | **데이터는 URL로 건넨다, 파일 경로가 아니라.** | 프론트가 `../data/`를 연다 |
| **P5** | **응답은 버전 경로 아래에.** 깨는 변경은 `/v2/`를 새로 내고 한동안 둘 다 낸다. | 경로에 버전이 없다 |
| **P6** | **한 응답 = 나중의 한 라우트.** 노선 36개를 한 파일에 뭉치지 않는다. | 서버 전환 때 다시 쪼개야 함 |

**P2의 유일한 예외**: 제휴 예약 링크. `TP_MARKER` 등 시크릿이 필요해 백엔드만 만들 수 있다.
사이트 내부 링크(`/routes/…`)는 전부 프론트가 만든다.

### 지금 위반하고 있는 것 (실측, 2026-09-08)

| 위치 | 위반 | 옮길 곳 |
|---|---|---|
| `collector/build_site.py:191` `route_page()` **180줄** | P1 — sqlite를 물고 HTML을 짠다 | 프론트 `site/route.py` |
| `collector/build_site.py:129` `deal_card()` 34줄 | P1 | 프론트 |
| `collector/build_site.py:100` `sparkline()` 29줄 | P1 (SVG) | 프론트 |
| `collector/build_site.py:384` `build_seo()` 20줄 | P1·P2 | 프론트 `site/seo.py` |
| `collector/theme.py` `BASE_URL` `SITE_NAME` `OG_IMAGE` `verification_meta` | P2 | 프론트 `site/shell.py` |
| `collector/discover_home.py`(프론트 소유)가 `theme`(백엔드)를 import | 경계 역행 | 둘 다 프론트로 |
| `docs/data/deals.json` — 프론트가 **파일 경로**로 읽음 | P4·P5 | `api.galmal.kr/v1/deals.json` |

`daily_min` `month_min` `weekday_min` `airline_min` `route_summary`(계 57줄)는 **통계 계산**이라
백엔드에 남는다. 다만 HTML이 아니라 **JSON으로 결과를 낸다.**

### 확인된 사실 — 걱정하지 않아도 되는 것

- `send_alerts.py`는 메일 HTML을 **DB 행에서 직접** 만든다. `deals.json`을 안 쓴다.
  → 계약을 바꿔도 알림 메일은 안 깨진다. (나중에 v1 API의 첫 외부 클라이언트로 돌리는 건 별건.)
- 백엔드 테스트 11개 중 프론트 자산(`discover.js|css`)을 읽는 것은 **0개**다.
- CORS는 지금 문제가 아니다. 프론트는 **빌드 타임에** API를 가져온다(브라우저가 아니라 Actions).
  런타임 fetch로 바꾸는 날에만 확인하면 된다.

---

## 3. v1 계약 (초안 — 확정본은 `CONTRACT.md`)

```
GET /v1/meta.json           schema·generated·수집 상태
GET /v1/deals.json          홈이 쓰는 전부 (현 deals.json과 동형)
GET /v1/routes/index.json   [{code, label, o, d}] — 네비·sitemap용
GET /v1/routes/{code}.json  노선 1개 통계 — 현재 route_page()가 conn에서 뽑던 값 전부
```

모든 응답의 공통 봉투:

```json
{ "schema": "v1", "generated": "2026-09-08T07:12:03+09:00", "...": "..." }
```

`generated`에 **오프셋을 반드시 포함**한다. 화면이 신선도를 표시하고 있고
(`SPEC.md` §CH3 `발견가 · N일 전 가격`), 날짜 경계에서 하루가 어긋나면 조용히 틀린다.

---

## 4. 단계

각 단계는 **사이트가 살아 있는 채로** 끝난다. 도메인은 M5에서만 건드린다.

### M0 — 계약 확정 · 기획

| 태스크 | 내용 |
|---|---|
| T1 | `CONTRACT.md`에 v1 4개 엔드포인트 스키마 전문 |
| T2 | `DECISIONS.md` 2026-09-08 — 결정·기각안(파일만 가르는 분리, deploy-pages만 하기) |
| T3 | `PROJECT.md` 목표 구조 반영 |
| T4 | 양 세션에 전달 |

**DoD**: 프론트·백엔드 양쪽이 "이 계약으로 짤 수 있다"고 회신. 못 짜는 항목이 있으면 T1로 되돌아간다.

### M1 — 백엔드가 JSON을 낸다 · 백엔드 (같은 레포 안)

| 태스크 | 내용 |
|---|---|
| T1 | `docs/v1/deals.json` 발행. **기존 `docs/data/deals.json`은 그대로 둔다** (프론트가 아직 씀) |
| T2 | `docs/v1/routes/{code}.json` 36개 — `route_page()`가 conn에서 뽑던 값을 **전부** |
| T3 | `docs/v1/routes/index.json`, `docs/v1/meta.json` |
| T4 | `test_contract.py` 확장 — v1 4종 검증 |

**DoD**: 지금 노선 페이지에 **표시되는 모든 숫자**가 JSON 안에 있다.
빠진 값이 하나라도 있으면 M2에서 프론트가 막힌다.
**롤백**: JSON을 추가로 낼 뿐이라 사이트 영향 0. 실패해도 되돌릴 게 없다.

### M2 — 프론트가 JSON에서 화면을 만든다 · 프론트 (같은 레포 안)

| 태스크 | 내용 |
|---|---|
| T1 | `site/` 신설. `discover_home.py`→`site/home.py`, `theme.py`→`site/shell.py` (백엔드에서 인수) |
| T2 | `site/route.py` — `v1/routes/*.json`에서 노선 페이지 36장 |
| T3 | `site/seo.py` — sitemap·robots |
| T4 | `site/build.py` 진입점. `--api <URL 또는 로컬 경로>` |
| T5 | **동등성 증명** |

**DoD (T5가 이 이전 전체의 관문이다)**:
`site/build.py`가 만든 37장이 현 배포본과 **diff 0**. 차이가 있으면 한 줄씩 설명하고
"의도한 개선"인지 "깨뜨린 것"인지 판정한다.
**+ 렌더 스크린샷 대조.** 이 프로젝트에서 반복 확인된 것: **테스트 통과는 화면이
멀쩡하다는 증거가 아니다** (z-index가 「(광고)」 고지를 가린 건, 막대 1개짜리 차트,
`[hidden]`이 `display:flex`에 밀린 건 3회 — 전부 테스트를 통과했다).
**롤백**: 크론은 아직 `build_site.py`를 부른다. 새 코드는 병행 존재일 뿐.

### M3 — 스위치 · 백엔드에서 HTML 삭제 · 백엔드+프론트

| 태스크 | 담당 | 내용 |
|---|---|---|
| T1 | 백 | 크론이 `publish.py`(JSON) → `site/build.py`(HTML) 순서로 부르게 |
| T2 | — | **하루 돌려서 정상 확인** (여기서 하루 쉰다) |
| T3 | 백 | `build_site.py`의 HTML 생성부 삭제 → `publish.py`로 개명. `docs/data/deals.json` 제거 |
| T4 | 백 | `theme.py` 삭제 |

**DoD**: 백엔드 코드의 문자열 리터럴에서 HTML 태그가 0건. 사이트 정상.
**롤백**: T3 전이면 커밋 되돌리기로 끝. T3 후 문제가 나면 재빌드.

### M4 — 레포 분할 · 사용자 + 양 세션

| 태스크 | 담당 | 내용 |
|---|---|---|
| T1 | **사용자** | `galmal-api`·`galmal-web` 생성 (**둘 다 public**) |
| T2 | **사용자** | secrets 8종을 `galmal-api`에 등록 |
| T3 | **사용자** | PAT 발급(무기한 fine-grained, `galmal-web`의 dispatch 권한만) → `galmal-api`의 secret |
| T4 | 백 | `collector/` `data/` `tests/` `collect.yml` 이동. Pages 켜고 `docs/v1/` 발행 |
| T5 | 프 | `site/` `assets/` `fixtures/` `deploy.yml` 이동 |
| T6 | 양쪽 | 배선: 백엔드 크론 끝 → `repository_dispatch` → 프론트 빌드·배포 |

**DoD**: `ryu-tomi.github.io/galmal-web`이 현 사이트와 동일하게 뜬다.
**도메인은 아직 안 건드렸다** — 이 시점에 galmal.kr은 구형이 계속 서빙한다.

### M5 — 도메인 이전 · 사용자

| 순서 | 내용 |
|---|---|
| 1 | `api.galmal.kr` CNAME → `ryu-tomi.github.io`, `galmal-api`에 커스텀 도메인 등록 |
| 2 | 프론트 빌드가 `https://api.galmal.kr/v1/…`을 보게 전환 |
| 3 | 구형 레포에서 커스텀 도메인 해제 |
| 4 | `galmal-web`에 `galmal.kr` 등록 → **HTTPS 인증서 발급 대기** (몇 분~수 시간) |
| 5 | 서치콘솔·서치어드바이저 소유확인 유지 확인 + 사이트맵 재제출 |

**DoD**: galmal.kr 정상 + https + 소유확인 유지. **다운타임이 있는 유일한 단계다.**

### M6 — 정리

| 태스크 | 담당 | 내용 |
|---|---|---|
| T1 | 사용자 | `promo-ticket-site` → `galmal-plan` rename 후 **private** |
| T2 | 기획 | `CLAUDE.md`를 3레포 판으로 재작성. 각 레포에 자기 `CLAUDE.md` + `../galmal-plan/` 참조 |
| T3 | 기획 | `PROJECT.md` 운영 정보 갱신, **이 문서 삭제** |

---

## 5. 위험

| # | 위험 | 대책 |
|---|---|---|
| R1 | **PAT가 조용히 만료** → 수집은 초록불인데 배포만 멈춘다. `BACKEND.md` BB18(몇 주째 죽어 있어도 아무도 몰랐던 건)의 재발 조건 | 무기한 fine-grained PAT + 백엔드 크론 끝에 "지금 배포된 사이트의 `generated`가 오늘 것인가" 점검 스텝. 아니면 잡을 실패로 |
| R2 | 백엔드는 성공, 프론트 빌드 실패 → **사이트가 어제 것** | 안전한 실패다(반쯤 쓰인 페이지가 안 나감). 다만 두 레포로 알림이 갈라지니 R1의 점검 스텝이 양쪽을 다 본다 |
| R3 | **M2 동등성 증명 실패** — JSON에 값이 빠져 있다 | M1 DoD를 엄격히. 빠지면 M1로 되돌아간다. 이게 M1/M2를 **같은 레포 안에서** 하는 이유다 |
| R4 | 도메인 이전 다운타임 · BE7 재실행 | M5를 마지막에 몰아서 한 번에. M4까지는 무중단 |
| R5 | worktree 3개 → clone 2개 + worktree 1개로 바뀐다 | M6에서 `CLAUDE.md` 재작성. 폴더는 형제로 유지해야 `../galmal-plan/` 참조가 산다 |
| R6 | `prices.db` 33MB | 파일만 옮긴다. DB 자체가 이력이라 git 이력은 안 가져가도 된다 |

---

## 6. 사용자만 할 수 있는 일 (세션이 대신 못 함)

- M4 T1 레포 2개 생성 (둘 다 **public** — private이면 Pages가 안 뜬다)
- M4 T2 secrets 8종 (`TP_TOKEN` `MAIL_ADDRESS` `MAIL_APP_PASSWORD` `ANTHROPIC_API_KEY` `TP_MARKER` `TP_TRIP_TRS` `TP_TRIP_P` `TP_TRIP_CAMPAIGN`)
- M4 T3 PAT 발급
- M5 전부 (DNS 레코드, Pages 커스텀 도메인, 검색엔진 재확인)
- M6 T1 rename + private 전환

**순서 경고**: 구형 레포를 private으로 돌리는 것은 **M6, 맨 마지막이다.**
M5가 끝나기 전에 누르면 galmal.kr이 404가 된다 (무료 플랜은 private 레포 Pages 불가).

---

## 7. 진행 현황

| 단계 | 담당 | 상태 |
|---|---|---|
| M0 계약 확정 | 기획 | ⬜ 대기 |
| M1 백엔드 JSON 발행 | 백엔드 | ⬜ |
| M2 프론트 화면 생성 | 프론트 | ⬜ |
| M3 스위치·HTML 삭제 | 백+프 | ⬜ |
| M4 레포 분할 | 사용자+양쪽 | ⬜ |
| M5 도메인 이전 | 사용자 | ⬜ |
| M6 정리 | 사용자+기획 | ⬜ |

**진행 중인 기존 작업과의 관계**: 프론트 CH4 T7(지도 미끄러짐)·CH5는 **M1 이전에 끝낸다.**
이전 중에 화면 기능이 움직이면 M2의 동등성 증명이 성립하지 않는다.
