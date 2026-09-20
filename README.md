<p align="center">
  <a href="https://galmal.kr"><img src="https://galmal.kr/assets/og.png" alt="갈래말래 — 어디, 갈까? 세계 지도에 오늘 싼 여행지가 찍혀 있다" width="720"></a>
</p>

# 갈래말래 — 백엔드

[![collect](https://github.com/RYU-TOMI/galmal-backend/actions/workflows/collect.yml/badge.svg)](https://github.com/RYU-TOMI/galmal-backend/actions/workflows/collect.yml)
[![test](https://github.com/RYU-TOMI/galmal-backend/actions/workflows/test.yml/badge.svg)](https://github.com/RYU-TOMI/galmal-backend/actions/workflows/test.yml)

**[api.galmal.kr/v1](https://api.galmal.kr/v1/meta.json) 을 발행하는 저장소입니다.** 매일 항공권 가격을 수집해 SQLite 에 쌓고, 평소 시세와 비교해 판정한 뒤, 정적 JSON API 로 내보냅니다. 화면(HTML)은 한 글자도 만들지 않습니다.

## 한눈에

<!-- 발췌: galmal-plan/PRODUCT.md §한 줄 소개 — 고칠 땐 거기부터 -->
> **어디, 갈까?**
> 목적지를 정하지 않은 사람에게, 평소보다 싸게 갈 수 있는 곳을 지도로 보여주는 한국 출발 항공권 발견 서비스.

이 저장소의 산출물은 JSON 입니다. 딜 하나는 이렇게 생겼습니다(`/v1/deals.json` 의 `deals[]` 원소, 값은 예시).

```jsonc
{
  "o": "SEL", "d": "TYO", "ko": "도쿄", "country": "일본",      // 허브 → 도시 코드. (o, d) 는 유일합니다
  "region": "jp", "haul": "short", "tier": "major",
  "tags": ["야경", "골목", "쇼핑", "미식", "도시"],              // 통제 어휘 — 순서가 곧 카드의 대표 태그
  "lat": 35.76, "lon": 140.39,
  "price": 224755, "transfers": 0, "dep": "2026-12-01", "ret": "2026-12-15", "nights": "14박15일",
  "median": 174134, "discount": 0,                              // 평소 시세(이전 관측 기간의 중앙값). 이력이 없으면 null
  "low": 140579, "obs_days": 14,                                // 이전 기간 최저가 · 관측 일수 — 오늘 값은 넣지 않습니다
  "when": "12월", "seen": "2026-09-15T15:53:39+09:00",          // 소스가 이 가격을 마지막으로 본 시각
  "route": "ICN-NRT",                                           // 노선 통계가 있으면 그 코드, 없으면 null
  "links": [{ "name": "스카이스캐너", "tag": "전체 비교", "ad": false, "url": "https://…" }, …]
}
```

## API 써보기

서버가 아니라 **GitHub Pages 가 서빙하는 파일**입니다. 인증·쿼리 파라미터·요청 제한이 없고, 하루 한 번 바뀝니다(`Cache-Control: max-age=600`).

| 엔드포인트 | 무엇 |
|---|---|
| [`/v1/meta.json`](https://api.galmal.kr/v1/meta.json) | 발행 시각 `generated` · 건수 · `preserved`(딜을 어제 것으로 보존했나) · 구독 메일 규약 |
| [`/v1/deals.json`](https://api.galmal.kr/v1/deals.json) | 발견 홈이 쓰는 전부 — 출발 허브 `origins` + `deals[]` |
| [`/v1/routes/index.json`](https://api.galmal.kr/v1/routes/index.json) | 통계가 있는 노선 목록 |
| [`/v1/routes/{code}.json`](https://api.galmal.kr/v1/routes/ICN-NRT.json) | 노선 1개 — 30일 최저가 추이 `trend` · 출발 월별 `months` · 요일별 `weekdays` · 항공사별 `airlines`(전부 표본 수 `n` 포함) |
| [`/v1/vocab.json`](https://api.galmal.kr/v1/vocab.json) | 참조 데이터 — 태그·`when`·지역·거리·허브 어휘와 지역 표시명 |

```bash
curl -s https://api.galmal.kr/v1/meta.json
curl -s https://api.galmal.kr/v1/deals.json | python -c "import sys,json; d=json.load(sys.stdin)['deals']; print(len(d), d[0]['ko'], d[0]['price'])"
```

- 모든 응답의 최상위에 `schema`(`"v1"`)와 `generated`(ISO 8601 + 오프셋)가 있습니다. **한 번의 발행이 낸 응답은 모두 같은 `generated`** 를 갖습니다 — 받는 쪽은 이 값으로 「섞인 스냅숏」을 잡을 수 있습니다. 예외는 하나로, 딜 보존일(`meta.preserved=true`)의 `deals.json` 만 더 이릅니다.
- **사실만 보냅니다.** `"2026-09"` 를 보내지 `"9월"` 을 보내지 않고, `wd=1` 을 보내지 `"월"` 을 보내지 않습니다. 얇은 표본도 버리지 않고 `n` 과 함께 냅니다 — 보여줄지는 받는 쪽이 정합니다.
- 필드 **추가**는 예고 없이 일어날 수 있습니다. 삭제·개명·의미 변경은 `/v2/` 로 갑니다.

## 세 저장소

<!-- 발췌: galmal-plan/PROJECT.md §저장소 셋 — 고칠 땐 거기부터 -->
| 저장소 | 무엇 | 서빙 |
|---|---|---|
| [`galmal-plan`](https://github.com/RYU-TOMI/galmal-plan) | 제품·스펙·결정 기록·계약의 **이유** · `design/` 목업 | — |
| **[`galmal-backend`](https://github.com/RYU-TOMI/galmal-backend)** ← 여기 | **수집·판정·v1 API·계약 정본 `contract/v1/`·크론** | **`https://api.galmal.kr/v1/`** |
| [`galmal-frontend`](https://github.com/RYU-TOMI/galmal-frontend) | v1 소비 · 화면 빌드 | `https://galmal.kr` |

경계는 **데이터 / 화면**입니다. 백엔드는 사실(JSON)만 내고 HTML 을 만들지 않습니다. 프론트는 DB 를 모르고 계약만 읽습니다.
**어느 기간을 보나(창)는 백엔드가, 보여줘도 되나(임계)는 프론트가** 정합니다.

## 어떻게 도나

<!-- 발췌: galmal-plan/PROJECT.md §하루의 흐름 — 고칠 땐 거기부터. 크론 시각은 이 저장소의 .github/workflows/collect.yml 이 정본 -->
```
galmal-backend   매일 아침(KST) 크론 — collect.yml
      ① 수집    fetch_prices   노선별로 깊게(날짜별 요금)        → offers        ┐
                fetch_breadth  공항별로 넓게(목적지당 최저가 1건) → broad_offers  ┴ data/prices.db (SQLite)
      ② 판정    detect_deals   노선·직항/경유별 30일 중앙값 대비 급락 → 구독 알림
      ③ 발행    publish.py     → docs/v1/*.json  ─ 딜이 하한선 미달이면 deals.json 은 어제 것을 남김
      ④ 커밋 → GitHub Pages(api.galmal.kr)
      │
      └─ API 가 방금 발행한 generated 를 실제로 서빙할 때까지 기다린 뒤
         repository_dispatch(api-updated · generated) ─┐
                                                       ▼
galmal-frontend  deploy.yml — v1 응답 전부를 한 스냅숏으로 받아 굽기 → GitHub Pages(galmal.kr) + build.json
      │
      └─ 백엔드 「상태 점검」이 api.galmal.kr/v1/meta.json 과 galmal.kr/build.json 을 읽어
         「API 가 멈췄나 · 사이트가 뒤처졌나 · 구독 주소가 갈렸나」를 확인
```

**서버가 없습니다.** `api.galmal.kr` 도 `galmal.kr` 도 GitHub Pages 가 파일을 내보낼 뿐입니다.
그래도 노선을 파일 하나로 묶지 않고 코드마다 쪼개 **HTTP 라우트처럼** 발행합니다 — 자체 서버가 생기는 날 DNS 만 옮기면 되고 프론트는 바뀌지 않습니다.

## 기술 스택

| 쓰는 것 | 안 쓰는 것 |
|---|---|
| Python 3.12 **표준 라이브러리** — `urllib` · `sqlite3` · `imaplib` · `smtplib` · `unittest` | 웹 프레임워크 · ORM · Node/npm |
| SQLite 파일 하나(`data/prices.db`) — 크론이 매일 커밋해 이력을 쌓습니다 | DB 서버 · 외부 스토리지 |
| GitHub Actions(크론) + GitHub Pages + 커스텀 도메인 | 서버 · 도메인 외 비용 |
| 가격 데이터: Travelpayouts Data API(v3 `prices_for_dates` · v2 `prices/latest`) | 타 비교사이트 크롤링 |
| 외부 의존성은 `anthropic` · `pydantic` **둘** — 항공사 프로모션 메일 파싱(`parse_mail.py`)에만 | 그 밖의 pip 패키지 |

## 폴더 구조

```
collector/                수집·판정·발행 — 진입점 publish.py
  fetch_prices.py         노선 상세 수집(config.ROUTES) → offers
  fetch_breadth.py        광역 수집(한국 5개 공항 → 전 목적지) → broad_offers. 도시 코드를 대표 공항으로 정규화
  detect_deals.py         노선·유형별 30일 중앙값 대비 급락 판정 (구독 알림용)
  discover_data.py        deals[] 생성 — 신선도 컷 · (허브, 도시) 최저가 1건 · median/low/obs_days · when 라벨 · 하한선 방어
  route_stats.py          노선 통계(창을 자른 집계). sqlite 전용 SQL 은 이 파일에만
  publish.py              v1 응답 5종을 docs/v1/ 에 기록 — 한 발행 = 한 generated
  dests.py                목적지 사전 — 한글명·지역·거리·태그 배정(DEST) · 좌표 · 도시↔공항 매핑. **계약 정본의 일부**
  affiliates.py           예약처 비교 링크 · 제휴 마커 · `ad` 판정
  timeutil.py             시각 처리 단일 출처 — 소스의 found_at 이 UTC 라는 사실을 여기서만 앎
  subscriptions.py        구독자 계산(받은편지함 = 구독자 DB, 명단은 저장하지 않음)
  send_alerts.py          구독 알림 발송(SMTP) · mail_ingest.py / parse_mail.py  프로모션 메일 수집·LLM 파싱
  mail_guard.py           메일 방어선 — 발신 도메인 허용 목록 · Gmail 인증(DMARC) 확인 · 실행당 상한
  config.py · db.py · labels.py
contract/v1/              계약 정본 — deal.schema.json(필드·타입·nullable·의미) · vocab.json(통제 어휘)
docs/v1/                  발행물(크론이 커밋) → GitHub Pages → api.galmal.kr/v1/
data/                     prices.db 등 수집 누적(크론이 커밋). 메일 본문 DB 는 .gitignore
tests/                    단위 테스트 + 계약 검증기(커밋된 발행물까지 검사)
.github/workflows/        collect.yml(크론) · test.yml(push 마다)
```

### 계약 정본

프론트와의 약속은 **이 저장소의 `contract/v1/` 과 `collector/dests.py`(`DEST` · `REGION_NAME`)** 가 정본입니다. **왜** 그렇게 정했는지는 [`galmal-plan/CONTRACT.md`](https://github.com/RYU-TOMI/galmal-plan/blob/main/CONTRACT.md) 에 있습니다 — 목록을 두 곳에 옮겨 적지 않습니다(갈린 적이 있습니다).
기획 결정 없이 `contract/` 를 바꾸지 않고, 바꿀 땐 커밋 메시지에 그 결정을 인용합니다. `tests/test_contract.py` 가 생산 로직과 **커밋된 `docs/v1/deals.json`** 둘 다를 이 스키마로 검사합니다.

## 로컬 실행 · 테스트

Python 3.12 만 있으면 됩니다(테스트는 설치할 것이 없습니다).

```bash
python -m unittest discover -s tests -t . -v      # 출력 끝의 OK 를 확인합니다

python collector/publish.py                       # v1 재발행 → docs/v1/  (.env 필요 — 아래 경고)
python -m http.server 8000 --directory docs       # http://localhost:8000/v1/meta.json
git checkout -- docs/v1                           # 검증용 재빌드는 커밋하지 않습니다(딜 목록은 시각에 따라 달라집니다)
```

`.env`(저장소 루트, git 제외)에 넣는 키입니다. 값은 적지 않습니다.

| 키 | 어디서 쓰나 | 없으면 |
|---|---|---|
| `TP_TOKEN` | `fetch_prices` · `fetch_breadth` (Travelpayouts Data API) | 수집이 즉시 멈춥니다 |
| `TP_MARKER` | `affiliates` — 제휴 마커 | 🔴 **예외 없이 제휴 링크만 빠집니다** |
| `TP_TRIP_TRS` · `TP_TRIP_P` · `TP_TRIP_CAMPAIGN` | Trip.com 제휴 래퍼(승인 전 — 없는 게 정상) | Trip.com 링크가 일반 링크로 나갑니다 |
| `MAIL_ADDRESS` · `MAIL_APP_PASSWORD` | `mail_ingest` · `subscriptions` · `send_alerts` (Gmail IMAP/SMTP) | 메일 계열이 멈춥니다 |
| `ANTHROPIC_API_KEY` | `parse_mail` | 메일 파싱이 멈춥니다 |

> 🔴 **재빌드는 `.env` 가 있는 환경에서만 해 주세요.** `TP_MARKER` 없이 `publish.py` 를 돌리면 사이트는 멀쩡해 보이고 수익 경로만 사라집니다. 빌드가 시작과 끝에 경고를 외치고, `tests/test_affiliates.py` 가 커밋된 발행물을 딜마다 검사합니다. 재빌드했다면 커밋 전에 확인합니다.
> ```bash
> python -c "import json; d=json.load(open('docs/v1/deals.json',encoding='utf-8')); print(len(d['deals']), sum(any(l.get('ad') for l in x['links']) for x in d['deals']))"
> # 두 숫자가 같으면 정상입니다
> ```

> ⚠️ 수집기(`fetch_*.py`)를 로컬에서 돌리면 `data/prices.db` 에 실제 행이 들어갑니다 — 커밋하지 않습니다. `mail_ingest.py` 는 메일함을 **소비**하므로(읽음 처리) 검증 목적으로는 돌리지 않습니다.

## 배포 · 운영

`collect.yml` 이 매일 예약 실행됩니다(시각은 그 파일의 `cron` 줄이 정본입니다 — GitHub 예약 실행은 1~2시간 늦게 시작할 수 있습니다). `main` 에 **크론이 매일 `data/` · `docs/v1/` 을 커밋**하므로 push 전에 반드시 pull 합니다.

- **손으로 돌릴 땐 `workflow_dispatch` 의 `skip_side_effects=true` 를 켭니다.** 메일 수집·LLM 파싱·알림 발송을 건너뜁니다 — 끄고 돌리면 메일함이 소비되고 구독자에게 실제 메일이 나갑니다.
- 시크릿은 **`production` 환경**에만 있습니다. 주소 변수 `API_URL` · `SITE_URL` 은 로그에 보여야 해서 secrets 가 아니라 vars 입니다.
- **한 스텝의 실패가 그날 수집분을 버리지 않도록** 수집·판정·발행은 전부 `continue-on-error` 입니다. 대신 마지막 **「상태 점검」**이 모든 스텝의 결과를 모아, 하나라도 실패했으면 **커밋 뒤에** 잡을 빨간불로 만듭니다 → GitHub 가 메일을 보냅니다.
- 한 번에 하나만 돕니다(`concurrency`). 수동 실행과 예약 실행이 겹치면 뒤 실행이 기다립니다 — 도는 중인 수집은 끊지 않습니다.

| 상태 점검이 보는 것 | 무엇을 막나 |
|---|---|
| 각 스텝 outcome · `preserved` | 초록불인데 몇 주째 죽어 있는 스텝 · 딜이 하한선 미달로 보존된 날 |
| 예약 실행이 UTC 자정 가까이(23·00시대)에서 돌았나 | 수집일 라벨(`fetched_date`, UTC 날짜)이 하루씩 흔들려 **이력에 구멍이 나는** 경우 |
| `api.galmal.kr/v1/meta.json` 의 `generated` 가 오늘/어제인가 | 수집은 되는데 **배포만 멈춘** 경우 |
| `galmal.kr/build.json` 의 `api_generated` | 프론트가 **다시 굽지 않는** 경우(dispatch 권한·토큰 만료) |
| `meta.subscribe.address` == 우리가 읽는 메일함 | 화면이 안내하는 주소와 파서가 읽는 주소가 갈리는 경우 — 반송조차 오지 않습니다 |

**「못 받음」은 통과가 아니라 실패입니다.** 확인은 초록불이 아니라 *API `meta.generated` == 사이트 `build.json.api_generated`, 둘 다 당일* 로 합니다.

## 설계에서 고른 것

- **나쁜 파일로 좋은 파일을 덮지 않습니다.** 딜이 30건 미만이거나 직전의 절반 미만이면 수집 사고로 보고 `deals.json` 을 쓰지 않습니다. 어제 데이터에 오늘 도장을 찍지 않으려고 `generated` 도 어제 것 그대로 두고, 그 상태는 `meta.preserved` 가 알려 줍니다 — [`discover_data.py`](collector/discover_data.py)
- **한 발행 = 한 `generated` 입니다.** 시각을 기본값 없는 필수 인자로 만들어, 새 응답이 넘기기를 빼먹으면 조용히 갈리는 대신 `TypeError` 로 터집니다. 규칙(보존일 예외 포함)은 테스트가 잠급니다 — [`publish.py`](collector/publish.py) · [`tests/test_publish.py`](tests/test_publish.py)
- **시각은 경계에서 aware 로 만듭니다.** 소스의 `found_at` 은 오프셋 없는 UTC 입니다. naive 시각과 그냥 빼서 9시간이 부풀었고, 그 때문에 멀쩡한 딜이 매일 잘려 나간 적이 있습니다. 변환을 아는 곳을 하나로 모으고, 기계용 날짜(UTC)와 제품용 날짜(KST)를 함수로 갈랐습니다 — [`timeutil.py`](collector/timeutil.py)
- **모르는 값을 지어내지 않습니다.** 이력이 없는 목적지의 `median` 은 현재가가 아니라 `null` 입니다. 「평소 시세」와 「최저가」에는 오늘 값을 넣지 않습니다 — 넣으면 "역대 최저냐"가 동어반복이 됩니다.
- **사실만 보내고 문장은 만들지 않습니다.** 규칙을 문서에만 두지 않았습니다 — 발행된 노선 응답에 `"9월"` · `"화요일"` 같은 화면 문자열이 새면 테스트가 잡습니다 — [`tests/test_publish.py`](tests/test_publish.py)
- **조용한 실패를 시끄럽게 만듭니다.** 수집이 전부 실패하면 exit 1, 제휴 시크릿이 없으면 빌드 끝에서 한 번 더 외치고, 커밋된 발행물 자체를 CI 가 검사합니다(발행물이 없으면 건너뛰지 않고 실패합니다). 네트워크 탓인 테스트만 skip 하되 stderr 에 줄을 남깁니다.
- **소스는 도시 코드로, 사전은 공항 코드로 말합니다.** 광역 응답의 `TYO` · `OSA` 를 못 알아봐 도쿄·오사카가 한 달간 피드에 없었습니다. 벤더 공식 참조로 매핑을 만들고, 저장은 대표 공항으로, 예약 링크와 계약의 `d` 는 다시 도시 코드로 넓힙니다 — [`dests.py`](collector/dests.py)
- **구독자 명단을 저장하지 않습니다.** 받은편지함을 매번 다시 읽어 구독 상태를 계산하고, 발송 로그에는 이메일 해시만 남깁니다. 저장소가 공개이기 때문입니다 — [`subscriptions.py`](collector/subscriptions.py)

각 결정의 실측값과 시행착오는 [`BACKEND.md`](BACKEND.md) 곁가지 백로그(BB)에 그대로 남아 있습니다.

## 문서

| 문서 | 무엇 |
|---|---|
| [`CLAUDE.md`](CLAUDE.md) | 이 저장소의 규칙 — 계약·크론·git·재빌드 |
| [`BACKEND.md`](BACKEND.md) | 작업 방식(챕터 → 태스크 → 스코프 잠금) · 맨 위 「▶ 지금 여기」가 현재 상태 · §7 곁가지 백로그(발견했지만 아직 안 고친 것) |
| [`contract/v1/`](contract/v1) | 계약 **정본** — 스키마와 어휘 |
| [`galmal-plan`](https://github.com/RYU-TOMI/galmal-plan) | 스펙(`SPEC.md`) · 계약의 이유(`CONTRACT.md`) · 결정 기록(`DECISIONS.md`) · 세 세션 공통 규칙(`SESSIONS.md`) |
| [`galmal-frontend`](https://github.com/RYU-TOMI/galmal-frontend) | 이 API 의 소비자 — v1 을 받아 화면을 굽습니다 |

2026-09-16 이전의 작업 이력은 분리 전 저장소 [`promo-ticket-site`](https://github.com/RYU-TOMI/promo-ticket-site)(→ `galmal-plan`)에 있습니다.

## 법적 고지

- 가격은 **조회 시점 기준**이며 실제 예약 가격은 예약처에서 달라질 수 있습니다.
- 응답의 `links[].ad` 가 `true` 인 링크는 제휴 링크입니다 — 그 링크로 예약하면 운영자가 수수료를 받습니다. 이용자가 내는 가격은 같습니다. 알림 메일에는 제목 `(광고)` 표기와 수신거부 방법을 넣습니다.
- 다른 비교 사이트의 DB 를 크롤링하지 않습니다 — 공식 API · 제휴 · 항공사 공지만 씁니다. 가격 데이터: Travelpayouts(Aviasales)
- 저장소는 공개입니다. `.env` · 구독자 이메일 원본 · 메일 본문 DB 는 커밋하지 않습니다.
