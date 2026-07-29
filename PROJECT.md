# 갈래말래 — 프로젝트 상태·로드맵·규칙

> 이 파일은 Claude(및 사람)가 세션 시작 시 프로젝트를 빠르게 파악하기 위한 단일 진실 문서다.
> 작업 진행/방향 전환 때마다 갱신한다. 상세 리서치 히스토리는 Claude 메모리의
> `flight-deal-site-research.md` 참조.

## 한 줄 요약
"시간 남는데 어디 싸게 갈까?"에 답하는 **항공권 특가 발견(discovery) 서비스**.
목적지를 검색하는 게 아니라, 예산·기분으로 **목적지를 정해준다**. 한국 출발 전용.

## 제품 방향 (중요 — 2026-07-30 전환)
- 초기엔 "특가 목록"이었으나, **발견(discovery)** 콘셉트로 전환.
- 경쟁(스카이스캐너·트립닷컴)은 "목적지 우선 검색". 우리는 "목적지를 정해주는" 틈새.
- 발견 모드는 지연 데이터(3일)에 **관대함**: 가격은 예약 약속이 아니라 "대략 이 정도" 신호.
  클릭하면 실시간 예약처로 넘어감.
- 메인 화면 = **인터랙티브 세계지도** (아래 로드맵 참조).

## 아키텍처 (핵심 원칙)
- **정적 사이트 + 서버 없음.** Python이 HTML/JSON을 미리 생성 → GitHub Pages 서빙. **비용 $0.**
- **매일 아침 크론**(GitHub Actions, KST 07:10)이 수집→판정→파싱→발송→사이트생성 전부 자동.
- 프론트 스택: **Python 정적 생성 + 순수 JS**. 지도만 **d3-geo**(브라우저 실행, 저장소에 벤더링).
  **Node/npm 빌드 없음.** 프레임워크(React 등) 안 씀 — 규모·SEO·속도상 불필요.

## 데이터 파이프라인 (2계층)
1. **노선 상세(depth)**: `fetch_prices.py` — 26개 노선을 v3 API로 날짜별 깊게 수집 → `offers` 테이블.
   특가 판정(`detect_deals.py`)·노선 상세 페이지·30일 히스토리 차트용.
2. **광역 발견(breadth)**: `fetch_breadth.py` — 한국 전 공항(ICN/GMP/PUS/TAE/CJU)을 v2 API로
   공항당 1회 호출, 목적지당 최저가 → `broad_offers` 테이블. "어디 갈까" 발견 피드용.
   품질 필터: `dests.py` 사전에 있는 목적지 + 신선도 3일 이내만.
- 메일: `mail_ingest.py`(수집, IMAP) → `parse_mail.py`(claude-haiku-4-5로 특가 추출) → `mail_deals`.
- 구독: `subscriptions.py`(받은편지함=구독자 DB, PII 미저장) → `send_alerts.py`(Gmail SMTP 발송).

## 주요 모듈 (collector/)
| 파일 | 역할 |
|---|---|
| `config.py` | 노선 상세 수집 대상 26노선, 특가 판정 기준(중앙값의 65%) |
| `dests.py` | 한국인 인기 목적지 ~90곳 사전 = 한글명+지역+분위기+haul. 발견 품질필터 겸용 |
| `db.py` | SQLite 스키마. offers/broad_offers/mail_deals/emails/alert_log |
| `fetch_prices.py` / `fetch_breadth.py` | 노선 상세 / 광역 발견 수집 |
| `detect_deals.py` | 직항/경유 분리 시세 대비 급락 판정 |
| `parse_mail.py` | 메일 본문 → 구조화 특가 (Claude API, Haiku, 제목 사전필터로 호출 절감) |
| `subscriptions.py` / `send_alerts.py` | 구독자 계산 / 알림 발송 |
| `affiliates.py` | 예약 링크 빌더 (Trip.com 미승인 → 현재 Aviasales 폴백) |
| `labels.py` / `theme.py` / `charts.py` | 라벨·도시명 / CSS·페이지셸 / 의존성 없는 SVG 차트 |
| `build_site.py` | **단일 진입점**. index + 노선26페이지 + sitemap/robots 생성 |

## 완료된 것 ✅
- 데이터 수집·특가 판정·메일 파싱·구독 알림 파이프라인 (크론 매일 무결점 가동 중)
- 노선 상세 페이지 26개 + sitemap/robots (SEO 기반)
- 갈래말래 브랜딩, 보딩패스 카드 UI, dataviz 팔레트
- **발견 데이터 계층**: fetch_breadth + dests + broad_offers (오늘 신선 목적지 51곳 확인)

## 진행 예정 — 발견 지도 UI (파트별, 각 파트 커밋)
> 사용자 비전: 접속 → 한국지도서 출발공항 선택 → 세계지도 열림 → 단계버튼으로 거리확장
> → 목적지 점 클릭 → 가격·날짜 카드. 지도는 "대충 모양"(schematic).

- [ ] **파트1. 지도 골격**: world.geojson(Natural Earth 110m 축소) + d3-geo 벤더링 + 한국 확대 화면 + 공항 5원
- [ ] **파트2. 출발지 선택 → 세계 열림**: 공항 클릭 시 projection 트윈 애니메이션
- [ ] **파트3. 목적지 점 찍기**: broad_offers → deals.json, 점 표시(쌀수록 강조), 정렬 확인
- [ ] **파트4. 단계 확장**: "더 멀리 보기" → 가까운곳→동남아→유럽·미주 순 노출
- [ ] **파트5. 점 클릭 → 카드**: 가격·날짜·분위기·예약 링크
- [ ] **파트6. 마감**: 기존 특가목록·구독 섹션 통합, 모바일, noscript 대체, 배포
- 상세 설계: `~/.claude/plans/cuddly-stirring-breeze.md`

## 이후 백로그
- 커스텀 도메인(galmal.kr 추천) → 구글 서치콘솔 등록 → 커뮤니티 시딩(뽐뿌 등)
- Trip.com 제휴 재신청(3개월 트래픽 후) — affiliates.py 코드는 대기 상태로 유지
- 항공사 프로모션 페이지 크롤링(두 번째 LLM 파싱 사용처)

## 작업 규칙 (반드시 지킬 것)
1. **파트마다 커밋.** 화면으로 확인 가능한 단위로 나눠 진행, 중간 점검.
2. **push 전 반드시 `git pull`.** 크론이 매일 `data/prices.db`·`docs/`를 커밋해 충돌 잦음.
   충돌 시: `git checkout --theirs data/prices.db` 후 `python collector/build_site.py` 재실행 → add/commit.
3. **로컬 점검 방법** (서버 없이 가능):
   - 개발 중: `docs/index.html` 브라우저로 열기. 단 `fetch()`는 `file://`서 CORS 막힘
     → 개발 중엔 **JSON을 HTML에 인라인**하면 파일 열기로도 지도 확인 가능.
   - 실배포 동일 확인: `python -m http.server 8000` → localhost:8000.
   - 최종: GitHub Pages(반영 1~2분).
4. **스택 고정**: Python 정적생성 + 순수 JS + 지도만 d3-geo(벤더링). Node/프레임워크 도입 금지.
5. **빌드 진입점은 `build_site.py` 하나.** 크론이 이것만 호출 → 새 페이지도 여기에 붙임.
6. **커밋 메시지 Co-Authored-By 라인 포함**(Claude Opus 4.8).

## 법적·보안 가드레일
- 타 비교사이트(네이버/스카이스캐너/플레이윙즈) **DB 크롤링 금지** (여기어때 판례, 민사 10억).
  항공사 자사 공지·공식 API·제휴만 사용.
- 제휴 링크: 제목 "(광고)" + 수수료 고지 필수(정보통신망법/공정위). 알림 메일에 수신거부 안내.
- 가격 표시엔 "조회 시점 기준, 실제 가격은 예약처 확인" 문구(데이터 3일 지연).
- **공개 저장소에 PII/시크릿 금지**: 구독자 이메일은 해시만(alert_log), 메일 본문은 로컬 전용
  (`data/emails_raw.db` gitignore), `.env` gitignore.

## 운영 정보
- 저장소: https://github.com/RYU-TOMI/promo-ticket-site (공개)
- 사이트: https://ryu-tomi.github.io/promo-ticket-site/
- GitHub Secrets: `TP_TOKEN`, `MAIL_ADDRESS`, `MAIL_APP_PASSWORD`, `ANTHROPIC_API_KEY`
  (Trip.com용 `TP_MARKER`/`TP_TRIP_TRS`/`TP_TRIP_P`/`TP_TRIP_CAMPAIGN`는 승인 후 등록 예정)
- 전용 메일: flightpromokr@gmail.com (항공사 뉴스레터 구독 + 구독 신청 접수)
- 비용: 도메인 미구매 상태라 현재 $0. 메일 파싱 API ~연 $2(월 지출 한도 설정됨).
