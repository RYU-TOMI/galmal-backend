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
| **P1** | **백엔드는 사이트에 올라가는 것을 만들지 않는다.** `docs/`에 들어가는 산출물 전부 — HTML·CSS·sitemap·robots. | 백엔드가 `docs/`에 HTML을 쓴다 |
| **P2** | **사이트 주소의 정본은 프론트다.** `BASE_URL`·`SITE_NAME`·`OG_IMAGE`·소유확인 메타는 `site/shell.py`. 백엔드는 **하드코딩하지 않는다.** | 백엔드 코드에 `https://galmal.kr` |
| **P3** | **프론트는 DB를 모른다.** | 프론트 파일에 `sqlite3` / `conn` |
| **P4** | **데이터는 URL로 건넨다, 파일 경로가 아니라.** | 프론트가 `../data/`를 연다 |
| **P5** | **응답은 버전 경로 아래에.** 깨는 변경은 `/v2/`를 새로 내고 한동안 둘 다 낸다. | 경로에 버전이 없다 |
| **P6** | **한 응답 = 나중의 한 라우트.** 노선 36개를 한 파일에 뭉치지 않는다. | 서버 전환 때 다시 쪼개야 함 |
| **P7** | **백엔드는 사실을, 프론트는 말을 낸다.** 임계·문구·포맷은 프론트. | 백엔드가 "표본이 부족합니다" |

### P1·P2가 「HTML 금지」가 아닌 이유 — 알림 메일 (백엔드 지적, 2026-09-08)

백엔드 세션이 짚었다: `send_alerts.py`가 백엔드에 남는데 그건 **메일 HTML을 만들고**
(`deal_line()`의 `<li>`, `build_mail()`의 본문) **사이트로 링크한다**
(`send_alerts.py:32` `SITE_URL = theme.BASE_URL + "/"`). 초안의 P1·P2가 그대로면 위반이다.

**예외로 때우지 않고 원칙을 다시 그었다.** 축이 「HTML이냐 아니냐」가 아니라
**「사이트냐 아니냐」**이기 때문이다.

| | 사이트 산출물 | 채널 페이로드 |
|---|---|---|
| 무엇 | `docs/`에 올라가 galmal.kr이 서빙하는 것 | 메일 본문. 나중에 알림톡·푸시·RSS도 여기 |
| 누가 | 프론트 | 백엔드 |
| 왜 | 화면이다 | 화면이 아니다. 웹 클라이언트가 렌더하지 않는다 |

메일은 **자체 서버가 생겨도 백엔드에 남는 것**(transactional email)이라, 미래 구조와도 맞는다.
그래서 P1은 「태그 금지」가 아니라 「사이트 산출물 금지」다.

**단, 문자열의 정본은 여전히 `COPY.md`다.** 렌더하는 모듈이 백엔드라고 해서
메일 문구를 백엔드가 지어내지 않는다. 지금과 같다.

### P2 — 백엔드가 주소를 필요로 하는 한 곳

알림 메일 링크. 여기서 하드코딩하면 `theme.py:29`가 경고하는 바로 그 일이 난다:
「도메인을 바꾸는 날 알림 메일만 옛 주소를 가리킨다 — 화면은 멀쩡하고 메일만 틀리므로 아무도 모른다」.

**해법: 환경변수 `SITE_URL`.** 도메인은 코드가 아니라 **배포 설정**이다.
자체 서버가 생기면 어차피 그렇게 관리한다.

⚠️ **이때 잃는 것이 있다.** 지금은 `tests/test_site_url.py:53`이
`send_alerts.SITE_URL`과 `theme.BASE_URL`이 갈라지지 않게 잠그고 있다.
분리 후 `BASE_URL`은 프론트 레포, `SITE_URL`은 백엔드 env — **아무도 대조하지 않는다.**

**대책(R1과 합침)**: 백엔드 크론 마지막 「상태 점검」이 `$SITE_URL/v1/meta.json`을 실제로 받아
`generated`가 오늘 것인지 본다. 주소가 틀리면 404로 실패하고, PAT가 죽어 배포가 멈춰도
같은 스텝이 잡는다. **한 점검이 두 가지를 다 막는다.**

**P2의 다른 예외**: 제휴 예약 링크. `TP_MARKER` 등 시크릿이 필요해 백엔드만 만들 수 있다.
사이트 내부 링크(`/routes/…`)는 전부 프론트가 만든다.

### 지금 위반하고 있는 것 (실측, 2026-09-08)

| 위치 | 위반 | 옮길 곳 |
|---|---|---|
| `collector/build_site.py:191` `route_page()` **180줄** | P1 — sqlite를 물고 HTML을 짠다 | 프론트 `site/route.py` |
| `collector/charts.py` 전부 (SVG 11군데 · `NOT_ENOUGH` 문구) | P1 — 순수 화면 코드 | 프론트 |
| `collector/labels.py`의 **포맷만** (`fmt_date` `fmt_month` `SQL_WEEKDAY`) | P1 | 프론트 |
| `tests/test_charts.py` | 프론트 코드를 테스트한다 | 프론트 |
| `collector/build_site.py:384` `build_seo()` 20줄 | P1·P2 | 프론트 `site/seo.py` |
| `collector/theme.py` `BASE_URL` `SITE_NAME` `OG_IMAGE` `verification_meta` | P2 | 프론트 `site/shell.py` |
| `collector/discover_home.py`(프론트 소유)가 `theme`(백엔드)를 import | 경계 역행 | 둘 다 프론트로 |
| `docs/data/deals.json` — 프론트가 **파일 경로**로 읽음 | P4·P5 | `api.galmal.kr/v1/deals.json` |

`daily_min` `month_min` `weekday_min` `airline_min` `route_summary`(계 57줄)는 **통계 계산**이라
백엔드에 남는다. 다만 HTML이 아니라 **JSON으로 결과를 낸다.**

`labels.py`의 **참조 데이터**(`city` `airline_name` `region_of`)도 백엔드에 남는다.
계약이 `o_name`·`d_name`·`airlines[].name`·`region`을 주므로 프론트는 이걸 안 봐도 된다.
**한 파일이 두 성격이라 쪼갠다** — 참조는 백엔드, 포맷은 프론트(프론트 발견).

### 🔴 옮기지 말 것 — 죽은 코드 (프론트 실측, 2026-09-08)

| | 상태 |
|---|---|
| `build_site.py:129` `deal_card()` 34줄 | **아무도 안 부른다** |
| `build_site.py:100` `sparkline()` 29줄 | `deal_card()`만 부른다 → 같이 죽었다 |
| 산출물 흔적 | `docs/index.html`·`docs/routes/*.html`에 `class="card"` 0건, `class="spark"` 0건 |

발견 홈이 옛 카드 홈을 대체하며 남은 잔해다. **M3에서 지운다. 옮기지 않는다.**
초안 표가 이 63줄을 프론트로 옮기라고 했는데 취소한다.

> 살아 있었다면 문제가 됐을 것이다 — `sparkline()`은 `daily_min(..., is_direct)`로
> **딜별** 추이를 그리는데 계약의 `trend`는 **노선 단위**라 `is_direct` 축이 없다.
> 죽어 있어서 문제가 안 됐다.

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

### `routes/{code}.json`이 담아야 할 것 (백엔드 확인, 2026-09-08)

노선 페이지가 지금 표시하는 숫자는 5종이다 —
`route_summary` · `daily_min` · `month_min` · `weekday_min` · `airline_min`.

**여기에 「표본이 부족하다」를 표현할 자리가 있어야 한다.** 백엔드 세션 지적:
지금은 양쪽 차트에 `len(rows) < 2` 임계가 걸려 `charts.NOT_ENOUGH` 문구가 나간다.
계약에 그 자리가 없으면 **프론트가 빈 차트를 그린다.**

**P7을 적용해 이렇게 나눈다:**

| | 누가 | 무엇 |
|---|---|---|
| 표본 수 `n` | 백엔드 | 사실. 모든 차트 블록에 **항상** 넣는다 |
| 임계 `n < 2` | 프론트 | 점 하나로 선을 못 긋는다는 건 **렌더링 판단**이다 |
| 「자료가 모자랍니다」 문구 | `COPY.md` | 지금도 그렇다 |

`null`로 얼버무리지 않는다 — "값이 없다"와 "표본이 모자라다"와 "0원이다"가 구분돼야 한다.

---

## 4. 단계

각 단계는 **사이트가 살아 있는 채로** 끝난다. 도메인은 M5에서만 건드린다.

### M0 — 계약 확정 · 기획

| 태스크 | 내용 |
|---|---|
| T1 | `CONTRACT.md`에 v1 4개 엔드포인트 스키마 전문 — **완료**(2026-09-08) |
| T2 | `DECISIONS.md` 2026-09-08 (1)(2)(3) — **완료** |
| T3 | `PROJECT.md` 목표 구조 반영 |
| T4 | 양 세션에 전달 |

**DoD**: 프론트·백엔드 양쪽이 "이 계약으로 짤 수 있다"고 회신. 못 짜는 항목이 있으면 T1로 되돌아간다.

### M1 — 백엔드가 JSON을 낸다 · 백엔드 (같은 레포 안)

| 태스크 | 내용 |
|---|---|
| T1 | `docs/v1/deals.json` 발행. **기존 `docs/data/deals.json`은 그대로 둔다** (프론트가 아직 씀) |
| T2 | `docs/v1/routes/{code}.json` 36개 — `route_page()`가 conn에서 뽑던 값을 **전부** + **버킷마다** `n`. `CONTRACT.md` §v1 4)의 「백엔드가 바꿔야 할 것」 5개 포함 |
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

> 🔴 **그래서 이전은 동작을 바꾸지 않는다.** 개선하고 싶은 게 있으면 **이전 전에**
> 현행 코드에서 고쳐 크론이 한 번 배포하게 하거나, **M3 이후에** 별도 챕터로 한다.
> 이전 중에 바꾸면 diff가 났을 때 **이전이 깨뜨린 건지 우리가 고친 건지 구분할 수 없다.**
> 프론트가 재현해야 할 현행 동작 3가지는 `CONTRACT.md` §「이전 중에는 동작을 바꾸지 않는다」.

> 🔴 **검수 시작 전에 기준선부터 확인한다** (프론트 제안):
> 비교 대상이 **BB29 수정 후 배포본**인가. 수정 전 화면과 비교하면 5장이 통째로 달라 보여서
> **규칙을 지켰는데도 실패로 판정하게 된다.** 걸리면 원인 찾는 데 오래 걸리는 종류다.
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
| T4 | 백 | `theme.py` 삭제. `send_alerts`가 도메인을 **env `SITE_URL`**로 받게 (P2). `test_site_url.py`는 프론트로 가고, 백엔드엔 `SITE_URL` 형식 검사만 남긴다 |

**DoD**: 백엔드 코드의 문자열 리터럴에서 HTML 태그가 0건. 사이트 정상.
**롤백**: T3 전이면 커밋 되돌리기로 끝. T3 후 문제가 나면 재빌드.

### M4 — 레포 분할 · 사용자 + 양 세션

| 태스크 | 담당 | 내용 |
|---|---|---|
| T1 | **사용자** | `galmal-api`·`galmal-web` 생성 (**둘 다 public**) |
| T2 | **사용자** | secrets 8종을 `galmal-api`에 등록 |
| T3 | **사용자** | PAT 발급(무기한 fine-grained, `galmal-web`의 dispatch 권한만) → `galmal-api`의 secret. **`SITE_URL` 변수도 같이** |
| T4 | 백 | `collector/` `data/` `collect.yml` 이동 + `tests/`(**`test_charts.py` 제외** — 프론트 코드를 테스트한다). Pages 켜고 `docs/v1/` 발행 |
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
| R1 | **PAT가 조용히 만료** → 수집은 초록불인데 배포만 멈춘다. `BACKEND.md` BB18(몇 주째 죽어 있어도 아무도 몰랐던 건)의 재발 조건 | 무기한 fine-grained PAT + 백엔드 크론 끝 「상태 점검」이 `$SITE_URL/v1/meta.json`을 받아 `generated`가 오늘 것인지 본다. 아니면 잡을 실패로 |
| R1b | **도메인이 조용히 갈라진다.** 지금은 `test_site_url.py:53`이 `send_alerts.SITE_URL`과 `theme.BASE_URL`을 대조하는데, 분리 후엔 각각 다른 레포/설정이라 **아무도 안 본다** | R1과 같은 점검이 막는다 — `$SITE_URL`이 틀리면 404로 실패한다. 별도 대책 불필요 |
| R2 | 백엔드는 성공, 프론트 빌드 실패 → **사이트가 어제 것** | 안전한 실패다(반쯤 쓰인 페이지가 안 나감). 다만 두 레포로 알림이 갈라지니 R1의 점검 스텝이 양쪽을 다 본다 |
| R3 | **M2 동등성 증명 실패** — JSON에 값이 빠져 있다 | M1 DoD를 엄격히. 빠지면 M1로 되돌아간다. 이게 M1/M2를 **같은 레포 안에서** 하는 이유다 |
| R4 | 도메인 이전 다운타임 · BE7 재실행 | M5를 마지막에 몰아서 한 번에. M4까지는 무중단 |
| R5 | worktree 3개 → clone 2개 + worktree 1개로 바뀐다 | M6에서 `CLAUDE.md` 재작성. 폴더는 형제로 유지해야 `../galmal-plan/` 참조가 산다 |
| R6 | `prices.db` 34.4MB | 파일만 옮긴다. DB 자체가 이력이라 git 이력은 안 가져가도 된다 |
| **R7** | 🔴 **시크릿 없이 재빌드하면 제휴 링크가 조용히 사라진다.** `affiliates.py:154`가 `if _env("TP_MARKER"):`라 마커가 없으면 **예외가 아니라 그냥 빠진다** — 사이트는 멀쩡히 뜨고 수익 링크 **125건**만 없어진다. 이전 중 M2·M3에서 재빌드를 반복하므로 **이 이전에서 가장 만나기 쉬운 함정**이다 (프론트가 실제로 겪음 → 백엔드 BB30) | ① 백엔드가 `build_site.py`에 **경고**를 넣는다(산출물 불변 → diff 0 안 건드림, 이전 전 가능) ② `CLAUDE.md`의 충돌 해결 절차를 고친다(아래) ③ 재빌드 후 `grep -c '"ad":true' docs/data/deals.json`으로 **125건을 눈으로 확인**한다 |

---

## 5b. 🔴 `CLAUDE.md` 충돌 해결 절차의 결함 (공용 파일 — 사용자 승인 필요)

`CLAUDE.md:85-86`이 이렇게 적혀 있다.

```
충돌 시: 생성물은 재빌드로 해결한다.
  git checkout --theirs data/prices.db → python collector/build_site.py → git add -A && git commit
```

**이 절차는 「재빌드하는 환경에 시크릿이 있다」를 가정한다.** 크론(Actions)은 있지만
`.env`는 gitignore라 **백엔드 worktree에만** 있다(`PROJECT.md` §작업 체제).
→ 프론트·기획 세션이 이 절차를 그대로 따르면 **제휴 링크 125건이 빠진 파일을 커밋한다.**
실제로 2026-09-08 프론트가 겪었고 커밋 직전에 잡았다.

**제안하는 수정** (사용자 승인 후 반영):

```diff
  - 충돌 시: 생성물은 **재빌드로 해결**한다.
    `git checkout --theirs data/prices.db` → `python collector/build_site.py` → `git add -A && git commit`
+   - 🔴 **재빌드는 `.env`가 있는 환경에서만 한다.** 시크릿 없이 돌리면 `affiliates.py`가
+     제휴 링크를 **경고 없이 빼고**(`ad:true` 125건 → 0건) 사이트는 멀쩡히 뜬다.
+   - `.env`가 없으면 재빌드하지 말고 **생성물은 `--theirs`로 원격 것을 취한 뒤**
+     그 구역 담당 세션에 재빌드를 요청한다.
+   - 재빌드했으면 커밋 전에 확인: `grep -c '"ad":true' docs/data/deals.json` → **125건**
```

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
