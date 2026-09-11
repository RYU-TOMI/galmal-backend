# FRONTEND.md — 프론트 세션 작업 방식

> **소유: 프론트 세션.** 다른 세션은 읽기만 한다.
> 담당 구역·git 규칙은 `CLAUDE.md`, 확정 스펙은 `DESIGN.md`, 데이터 계약은 `CONTRACT.md`,
> 왜 그렇게 정했나는 `DECISIONS.md`. **이 문서는 "어떻게 일하는가"만 다룬다.**

## 왜 이 문서가 있나
사용자는 백엔드 전공이라 **프론트 코드를 리뷰하지 않는다.** 여기서 두 가지가 따라온다.

1. **스코프가 새는 걸 사용자가 못 잡아준다** → 규칙으로 막아야 한다. (기능 하나 고치다 옆길로 우다다 파고드는 문제)
2. **리뷰는 코드가 아니라 화면으로 한다** → 보고는 항상 "어디를 열고 뭘 눌러야 뭐가 보인다"로 낸다.

---

## 1. 작업 단위 3계층

| 단위 | 크기 | 규칙 |
|---|---|---|
| **챕터** | 기능 영역 1개 (예: 지도 무대, 필터·정렬) | **세션 1개 = 챕터 1개.** 시작 전 태스크 목록을 사용자에게 승인받는다. |
| **태스크** | **커밋 1개** | 화면에서 확인 가능한 최소 변화. 한 태스크가 여러 화면을 건드리면 잘못 쪼갠 것. |
| **곁가지** | 작업 중 발견한 딴 문제 | **지금 고치지 않는다.** `BACKLOG.md`에 한 줄 적고 넘어간다. |

### 스코프 잠금 — 가장 중요한 규칙
- 챕터 시작 시 **건드릴 파일과 태스크 목록을 먼저 못 박는다.** 목록에 없는 파일은 열어보되 고치지 않는다.
- 작업 중 다른 문제를 발견하면 → `BACKLOG.md` 한 줄 + 보고서에 "발견했고 **안 고쳤습니다**" 명시.
- 유일한 예외: **그걸 안 고치면 지금 태스크가 성립하지 않을 때.** 이때도 왜 어쩔 수 없었는지 보고한다.
- "이왕 하는 김에"는 금지어다. 이왕 할 거면 다음 챕터에서 한다.

---

## 2. 챕터 진행 5단계

1. **스펙 확인** — `DESIGN.md`·`DECISIONS.md`에서 이 챕터의 확정 사항을 찾아 **근거로 인용**한다.
   스펙이 없거나 모호하면 **구현하기 전에 사용자에게 묻는다.** 디자인·UX 결정은 기획 세션 몫이므로 추측해서 만들지 않는다.
2. **태스크 쪼개기** — 태스크 목록 + 건드릴 파일을 제시하고 승인받는다. → 스코프 잠금.
3. **구현** — 태스크 1개 = 커밋 1개. 태스크 끝날 때마다 확인 절차를 낸다.
4. **QA** — 아래 체크리스트 전 항목. 통과 못 하면 챕터를 끝내지 않는다.
5. **핸드오프** — main 병합 → `BACKLOG.md` 갱신 → 핸드오프 메모(§7) → 세션 종료.

---

## 3. QA 체크리스트 (챕터 끝, 전 항목)

- [ ] **콘솔 에러 0** (경고도 새로 생기면 안 됨)
- [ ] **화면 폭 3종**: 데스크톱 1440 / 태블릿 900 / 모바일 390
- [ ] **딜이 적은 출발지**에서도 안 깨짐 — 대구(7건)·제주(8건)가 서울(57건)보다 잘 깨진다
- [ ] **필터 켠 상태** / **매칭 0건 상태**(빈 상태 문구가 떠야 함)
- [ ] **3단계 뷰 전부**: 가까운 곳 · ＋동남아 · ＋유럽·미주
- [ ] **확장 상세 열린 채로 다른 조작**(정렬 변경, 단계 변경, 필터 변경)
- [ ] 데이터 0건인 날 가정 — `deals: []`여도 화면이 살아 있어야 함 (`CONTRACT.md` §3)
- [ ] `node --check docs/assets/discover.js` — 문법 오류 사전 차단
- [ ] 🔴 **정의 없는 호출 확인** — `node --check` 는 **문법만** 본다. 함수를 지우고 호출부를 남기면
      통과하는데 런타임에 `ReferenceError` 로 **렌더가 통째로 죽는다.** 실제로 겪었다(2026-09-04):
      `pinBoxes` 를 블록 교체 중에 지웠는데 `placeLabels` 가 계속 불러서 **핀 0개·피드 0장**이 됐고,
      `node --check` 는 OK 였다. 화면을 안 찍었으면 못 봤다.
      ```
      python - <<'EOF'
      import io,re
      s=io.open('docs/assets/discover.js',encoding='utf-8').read()
      defs=set(re.findall(r'function\s+([A-Za-z_$][\w$]*)\s*\(',s))
      calls=set(re.findall(r'(?<![\w$.])([A-Za-z_$][\w$]*)\s*\(',s))
      print(sorted(calls-defs))   # d3 반환값·내장은 오탐이니 눈으로 걸러 본다
      EOF
      ```
- [ ] 🔴 **첫 화면을 반드시 찍어 본다.** 화면0이 없어진 뒤로 `boot()` 이 **파싱 중**에 돈다 —
      그 시점엔 `svg.getScreenCTM()` 이 없어 UI 회피가 무력화되고, 재렌더 계기가 없으면
      **그 상태가 첫 화면으로 굳는다.** 실측: `삿포로` 라벨이 도크 안에 36.3×17.0px 통째로 들어갔다.
      레이아웃에 의존하는 계산은 `requestAnimationFrame` 뒤에 한 번 더 돌려야 한다.

> `node --check`는 **문법 검사에만** 쓴다. 빌드에 node를 끌어들이는 게 아니므로
> "Node/npm 빌드 도입 금지"(`CLAUDE.md`)에 어긋나지 않는다. 배포물은 여전히 순수 JS 파일 그대로다.

---

## 4. 확인·리뷰 방법

### 미리보기
```
python -m http.server 8000 --directory docs    →   http://localhost:8000
```

### 리빌드가 필요한 경우 / 아닌 경우 (중요)
| 고친 파일 | 리빌드 | 방법 |
|---|---|---|
| `docs/assets/discover.js` · `discover.css` | **불필요** | `index.html`이 상대경로로 참조 → **새로고침만** |
| `collector/discover_home.py` (셸 HTML) | 필요 | 아래 절차 |

```bash
python collector/build_site.py
git checkout -- docs/data docs/routes docs/sitemap.xml   # 백엔드 산출물 되돌리기
```

> ⚠️ **위 경우 외에는 `build_site.py`를 돌리지 않는다.**
> 돌리면 그날 DB로 `deals.json`이 재생성되어 **픽스처가 바뀌고**(예: 103건→94건),
> 노선 페이지 26개 + sitemap까지 전부 커밋 노이즈가 된다. 그건 백엔드 세션의 산출물이다.

#### 🔴 그 전에 — **프론트 worktree 에서는 재빌드하지 않는다** (2026-09-08 `CLAUDE.md` 개정)

`.env` 는 gitignore 라 **백엔드 worktree 에만 있다.** 시크릿 없이 `build_site.py` 를 돌리면
`affiliates.py` 가 제휴 링크를 **경고 없이 뺀다**(`ad:true` 125건 → 0건). 예외도 안 나고
사이트도 멀쩡히 뜬다. 2026-09-08 에 실제로 겪었고 커밋 직전에 잡았다.

**생성물이 충돌하면**: `git checkout --theirs` 로 원격 것을 취하고 백엔드에 재빌드를 요청한다.
크론이 다음 날 어차피 다시 만든다. 아래 「인라인 데이터 맞추기」는 **이미 재빌드해 버렸을 때의
복구 절차**다 — 먼저 쓸 절차가 아니다.

🔴 **`CLAUDE.md:93` 의 확인 명령은 그대로 쓰면 틀린 값이 나온다.**
`deals.json` 은 **개행이 없는 한 줄**이라 `grep -c`(줄 수)는 **건수와 무관하게 항상 1** 이다.
「→ 125건」은 절대 안 나오고, 125건 중 3건만 남아도 똑같이 `1` 이다. 건수를 세려면:

```bash
grep -o '"ad":true' docs/data/deals.json | wc -l    # 125
```

`CLAUDE.md` 는 공용 파일이라 프론트가 못 고친다. 기획·백엔드에 알렸다(2026-09-08).

#### 🔴 재빌드 뒤 반드시 — `index.html` 인라인 데이터를 커밋본으로 맞춘다

**`docs/data/deals.json`만 되돌리면 안 된다.** `index.html`은 딜을 **인라인**하므로,
되돌린 뒤에도 **내 로컬 DB로 만들어진 딜이 페이지 안에 남는다.**

실제로 당했다(2026-09-02, CH2 T1): 재빌드가 **121건**을 인라인했는데 커밋본은 **127건**이었다.
`updated` 시각만 맞췄으면 **121건 데이터에 127건 시각표**가 붙어 더 나빠질 뻔했다.

```python
# git 의 커밋본을 원본으로 삼아 index.html 의 window.__DEALS 를 통째로 교체한다
raw = subprocess.run(['git','show','HEAD:docs/data/deals.json'],capture_output=True).stdout.decode()
h = re.sub(r'(window\.__DEALS=)\{.*?\}(;</script>)', lambda m: m.group(1)+raw.strip()+m.group(2), h, flags=re.S)
```

**확인할 것** — 셋 다 통과해야 커밋한다.
1. 인라인 딜 수 = `git show HEAD:docs/data/deals.json` 의 딜 수
2. 인라인 `updated` = 커밋본 `updated`
3. 딜 배열이 **바이트 동일**(`inl['deals'] == com['deals']`)

> **작업 트리의 `deals.json` 을 "커밋본"이라고 읽지 말 것.** 재빌드가 이미 덮어썼다.
> 반드시 `git show HEAD:...` 로 읽는다 — 그렇게 안 해서 검증이 항상 통과하던 적이 있다(T1).

### ⚠️ 확인 절차는 렌더 경로 **전체**를 재현하고 낸다
함수 하나만 격리해 테스트하고 "화면에 이게 보일 것"이라고 안내하면 **거의 틀린다.**
2026-09-01 B25 수정 때 확인 절차를 **두 번 연속 틀리게** 안내했다.

| 빠뜨린 것 | 결과 |
|---|---|
| hero 카드가 정렬과 무관하게 맨 위 고정(`render()`의 `order`) | "1위가 괌"이라 했는데 실제 1위는 hero(도쿄) |
| 단계 필터가 도시를 걸러냄(`visibleCities()`의 `upto`/`showMinor`) | 괌은 `haul=sea`라 `가까운 곳` 단계에 아예 없음 |

**피드 한 장이 화면에 뜨기까지 거치는 관문**(순서대로):
`visibleCities()` 단계·LOD 필터 → `dimmed()` 필터 dim → 정렬(`cmp[sortMode]`) → hero 선정·맨 앞 고정 → 렌더

- 검증 스크립트는 **이 사슬을 전부 재현**한다. 실제 `discover.js`에서 함수를 발췌해 쓰면 코드와 어긋나지 않는다.
- 사용자에게 낼 때는 **어느 출발지·어느 단계·어느 정렬**인지까지 명시한다. "1위" 대신 "hero 아래 첫 카드".
- 사용자가 "다르다"고 하면 **먼저 내 절차를 의심한다.** 두 번 다 코드는 맞았고 안내가 틀렸다.

### 사용자용 확인 가이드 (코드 안 보고 검수하기)
> 사용자는 백엔드 전공이라 프론트 코드를 읽지 않는다. 이 4가지면 **코드 없이 화면만으로** 검수가 된다.
> 새 세션은 사용자가 이 도구들을 이미 안다고 가정하지 말고, 필요할 때 이 절을 안내한다.

| 조작 | 무엇 | 언제 쓰나 |
|---|---|---|
| **F12 → Console 탭** | JS 에러 로그 | **가장 값어치가 큼.** 빨간 줄이 있으면 "코드가 깨진 것", 없으면 "코드는 도는데 디자인이 이상한 것" — 이 구분만 알려줘도 원인 추적이 몇 배 빨라진다 |
| **Ctrl+Shift+M** | 모바일 화면 흉내 | 폭을 `390`으로 넣으면 폰 크기. 실기기 없이 모바일 확인 |
| **Ctrl+Shift+R** | 하드 새로고침(캐시 무시) | **"고쳤다는데 화면이 그대로"의 90%가 캐시다.** 그냥 F5 말고 이걸로 |
| **F12 → Network → Disable cache** | 캐시 영구 무시 | 개발자 도구 열려 있는 동안 적용. 체크해두면 위 문제가 아예 안 생김 |

- 자동 새로고침(hot reload)은 **우리 스택에 없다.** Vite/Next 같은 번들러가 주는 기능인데 npm 도입 금지라 쓸 수 없다.
  대신 **빌드 단계가 없어서** `discover.js`를 고치면 그게 곧 브라우저가 읽는 파일이다 → 새로고침이 사실상 즉시다.
- 비유(사용자가 백엔드 전공이므로): 팀원들이 쓰는 dev server는 `uvicorn --reload` 같은 것이고,
  우리는 컴파일이 없어서 **브라우저 새로고침 = 재시작**이다.

### ⚠️ 콘솔 한글 깨짐 — 실측값을 보고하기 전에 반드시 확인
이 환경(Windows, cp949 콘솔)에서 **파이썬 출력의 한글이 깨진다.** 숫자는 멀쩡한데 글자만 깨지므로
**"수치는 맞고 라벨만 틀린" 보고**가 나오기 쉽다. 실제로 그렇게 틀린 값을 다른 세션에 전달한 적이 있다(2026-08-22, 태그 라벨 3개).

```python
import sys; sys.stdout.reconfigure(encoding='utf-8')   # 한글 출력 전 항상
```
- 깨진 출력(`�غ�` 같은 것)을 보고 **라벨을 추측해서 채우지 않는다.** 다시 돌린다.
- 한글 값을 다른 세션·사용자에게 보고할 때는 **UTF-8로 다시 뽑은 출력을 근거로** 한다.

### push 기준 (2026-08-22 사용자 결정)
| 대상 | 기준 |
|---|---|
| **프론트 소유 문서** (`FRONTEND.md` · `BACKLOG.md`) | **묻지 않고 자동 push.** 다른 세션이 읽어야 의미가 있고, 되돌리기 쉽다 |
| **코드** (`discover.js` · `discover.css` · `discover_home.py`) | **승인 전까지 커밋하지 않는다.** 작업 트리에만 두고, 사용자가 화면으로 확인한 뒤 커밋·push (2026-09-01 사용자 결정) |
| **공용 파일** (`CLAUDE.md` 등) | 변경 자체를 먼저 확인받는다 (`CLAUDE.md` 규칙) |

> ⚠️ **왜 "커밋도 하지 않는다"인가** — `git push`는 브랜치 단위라 문서만 골라 올릴 수 없다.
> 코드를 미리 커밋해두면 **다음 문서 자동 push에 딸려 올라간다.** 실제로 2026-09-01 B25 수정이
> 그렇게 승인 없이 main에 올라갔다. 커밋 자체를 미루면 이 경로가 막힌다.
>
> **문서를 push하기 전 매번 확인한다:**
> ```bash
> git diff --name-only origin/main..frontend   # .md 외 파일이 있으면 push 보류
> ```

- push는 `frontend` → `origin/frontend` → `origin/main`(fast-forward) 순. 그 전에 반드시 `git fetch && git merge origin/main`.
- 문서를 자동 push해도 **무엇을 올렸는지는 보고에 always 남긴다.** 조용히 올리지 않는다.

### 보고 형식 (태스크마다)
```
바꾼 것: (1줄)
확인: 1) 어디를 연다  2) 뭘 누른다  3) 뭐가 보여야 한다
```
+ 스크린샷 (Chrome 확장 연결 시 프론트 세션이 직접 촬영해 첨부)

---

## 4-1. 말투 (2026-08-22 사용자 확정 — 바꾸지 말 것)

사용자가 **세션 3개를 말투로 구분한다.** 기획·백엔드와 톤이 겹치면 누가 말하는지 알 수 없게 된다.
아래는 프론트 세션에 배정된 말투이며, **사용자 보고와 다른 세션에 보내는 메시지 양쪽에 똑같이 적용한다.**

**쓴다**
- 한국어 존댓말(`합니다`체). 담백하게.
- **결론 먼저, 근거는 뒤.** "제가 틀렸습니다" → 왜 → 어떻게 막을지.
- **숫자로 말한다.** "많다" 대신 "103건 중 71건(69%)".
- 불확실하면 불확실하다고 쓴다. "확인 필요", "단정하지 않음".
- 사용자가 프론트를 모른다는 전제로 **비유를 쓰되 깔보지 않는다**(백엔드 전공이므로 `uvicorn --reload` 같은 비유가 통한다).
- 표·굵게는 핵심에만. 끝에 **무엇을 결정해줘야 하는지** 분명히.

**안 쓴다**
- 과장·감탄사·이모지·영업 멘트("완벽합니다", "훌륭한 질문입니다").
- 실수했을 때의 반복 사과·자책. **한 번 인정하고 원인·재발방지로 넘어간다.**
- 안 한 일을 한 것처럼 쓰는 표현. 못 한 검증은 "못 했습니다"라고 쓴다.
- 사족. 요약을 요약하지 않는다.

## 5. 코드 규칙

- **스택 고정**: 순수 JS + `d3-geo`만. npm·프레임워크·런타임 CDN 금지(폰트 예외). — `CLAUDE.md`
- **기존 코드 스타일을 따른다**: 현재 `discover.js`는 IIFE + `var` + ES5 문법. 새 코드도 여기 맞춘다(혼재 금지).
- **계약 방어**: `deals.json` 필드는 항상 `dl.x || 기본값`으로 읽는다. 백엔드가 0건을 주는 날도 안 깨져야 한다.
- **파생 로직은 프론트 소유**: 가격 포맷·"왜 지금" 훅·태그 색·LOD·핀 색 농도는 직접 계산한다. 백엔드에 필드로 요청하지 않는다. — `CONTRACT.md`
- **없는 필드를 쓰지 않는다**: 백엔드 필드가 필요하면 `CONTRACT.md` 변경 절차(사용자를 통해 백엔드 세션에 전달). 추측 필드·더미 데이터 금지.
- **가짜 데이터 절대 금지**: 하드코딩 배열로 그래프를 그리지 않는다. 신뢰가 유일한 자산이다. — `DECISIONS.md`(가짜 가격 그래프 제거, 2026-08-06)
- **죽은 코드는 남기지 않는다**: 제거할 때 커밋 메시지에 왜 죽었는지 쓴다.

---

## 6. 챕터 로드맵

| # | 챕터 | 범위 | 상태 |
|---|---|---|---|
| CH0 | 기반 정리 | 작업 규칙 문서화 · 죽은 코드 제거 · 예산 dim 버그 | ✅ 완료 |
| CH1 | 지도 무대 | 단계 라벨 · 스테퍼 · LOD · far 뷰 계산 · 렌더 구조 · 트윈 · 라벨 배치 | ✅ 완료 (+ 2026-09-03 후속: 라벨이 핀·출발지 회피 `eee61e1`) |
| **CH2** | **필터·정렬** | `when` 비교(B26) · 날짜 8칩 · 며칠 축 · 예산 범위·바로가기 칩 · 분위기 6종 · 0곳 칩 비활성 · 접힌 도크 조건 표시 · 필터 시 far 뷰 · 태그 사진 위 · 도크 라벨 제외 | ✅ **완료** (2026-09-03) |
| CH3 | 카드 피드 | 화면0 제거 · hero 큐레이션 · 빈 상태 3종 · 할인 도장 3티어 · 훅 줄 폐기 · 신선도 배지 | ✅ **완료** (2026-09-04) |
| CH4 | 상세 전환 | **딥링크(IA-2)** · 사라진 딜(F5) · 공유 버튼 · `links` 0건(F4) · 카드가 도크 회피 · 열고닫기 | ✅ **완료** (2026-09-05) |
| CH5 | 모바일 | 3단 시트(peek/half/full) · 핀 탭=peek(B10) · 사진 폭 태그 규칙 · 펼친 도크=하단 시트 · CDP 측정 도구 | ✅ **완료** (2026-09-05) |
| CH6 | 접근성·마감 | 키보드 조작 · aria · noscript · 사진 정책 · 성능 | 🔴 **중단** — 이전 후 재개(§8-3) |
| **M2** | **레포 분리 — 화면 인수** | `site/` 신설 · 노선 36장 · 홈 · sitemap · 픽스처 | ✅ **완료** (2026-09-09) — 동등성 39/39 (§8-11) |

- 순서는 **바닥부터 위로**: 정리 → 지도(무대) → 필터(입력) → 피드·상세(출력) → 모바일 → 마감.
- 챕터를 건너뛰지 않는다. 급한 게 생기면 로드맵을 고치고 그 이유를 남긴다.

### CH2 진행 (2026-09-02 밤)

| 태스크 | 내용 | 커밋 |
|---|---|---|
| T1 | `dateWindow()` 제거 → `when` 비교 · 날짜 칩 5 → 8종 (B26) | `ae91c1d` |
| T2 | `며칠` 축 신설 (1~3박 / 4~6박 / 7~13박 / 2주 이상) | — |
| T3 | 예산 슬라이더 범위를 출발지 데이터에서 (B5) | `da97992` |
| T4 | 필터를 켜면 `아주 멀리` 뷰 + 라벨은 매칭에게만 (B6) | `cff2a4f` |
| T5 | 접힌 도크가 개수 대신 조건을 보여준다 (B7) | `e401ec9` |
| T6 | 분위기 칩 5 → 6종 + 건수·0곳 비활성 (C-10) | `e2d87bb` |
| T7 | 도크·줌 버튼 자리를 라벨 배치에서 제외 (B16 라벨 부분) | `d05bba6` · `124343f` |
| T8 | 태그를 사진 위로, 작은 카드에서 제거 (C-13) | `d93f56c` |
| T9 | 예산 바로가기 칩 30만·50만·100만·상관없어 | `c6f8e72` |
| T10 | 예산 히스토그램 (트랙과 같은 **선형** 눈금) | `987cad9` |

- **T10 눈금 결정**: SPEC 안에서 로그/선형이 두 번 반대로 확정돼 있어 기획에 확인을 요청했고,
  기획이 **재측정 후 로그를 철회**했다(`SPEC.md` `c6de197`). 근거였던 "고가 구간이 비어 있다"가
  사실이 아니었다 — 서울 70~130만에 29건(41%). 트랙·히스토그램 **둘 다 선형**, `step` 5만 유지.
- 로드맵의 "검색 한 줄 재설계"는 **뺐다.** `SPEC.md:328`이 "위치 = 지도 우측 하단 플로팅 도크(헤더 바 아님)"로
  확정하면서 대체됐다. 로드맵 쪽이 확정 전 메모였다.
### 화면 확인 — 브라우저 확장 없이 (2026-09-03 도입)

확장이 안 붙는 시간대에도 **헤드리스 크롬으로 PNG를 구워 직접 읽는다.** 기획 세션이 알려준 방법이고,
실제로 이걸로 **z-index 버그와 칩 숨김 오구현**을 잡았다(`0c35d09`). 스크립트는 스크래치패드에 둔다.

```
chrome.exe --headless=new --disable-gpu --hide-scrollbars --force-device-scale-factor=2   --screenshot=OUT.png --window-size=1440,900 --virtual-time-budget=9000 file:///.../docs/_shot.html
```

- **빌드 파이프라인이 아니다.** 사람이 확인용으로 한 번 돌린다 → "Node 금지·CDN 의존 0"과 무관하다.
- 출발지 선택·칩 클릭 같은 조작은 `docs/_shot.html`(임시 복사본)에 스크립트를 주입해 재현한다.
  `docs/` 안에 둬야 `assets/` 상대경로가 산다. 다 찍고 반드시 지운다.
- 🔴 **`--window-size` 로는 모바일 폭을 못 만든다.** 창에 **최소 폭(~500px)** 이 걸려 있어서
  `--window-size=390` 을 줘도 **실제 뷰포트는 489px**(dsf 2) 또는 500px(dsf 1)이다.
  `--window-size=200` 도 512px 이고 `--headless=old` 도 512px 다. 데스크톱은 정확하다(1440 → 1418).
  **그래서 "390px 에서 확인했다"고 보고한 것들이 전부 489px 이었다** — B36(무대가 뷰포트보다 넓다)은
  그 착오에서 나온 오진이다.
  → **CDP `Emulation.setDeviceMetricsOverride` 로 뷰포트를 직접 지정한다**(`cdp.py`, 스크래치패드).
  `--remote-debugging-port` 로 띄우고 웹소켓으로 붙는다. 표준 라이브러리만 쓴다.
  ```
  with Chrome() as c: c.shot(url, out, width=390, height=844, dsf=2, mobile=True)
  ```
  화면 폭이 관련된 확인은 **반드시 실제 `clientWidth` 를 같이 찍어 본다.**
- 🔴 **같은 URL 로 `Page.navigate` 하면 재로드가 안 된다.** 폭을 바꿔 가며 같은 주소를 다시
  열면 이전 상태가 남는다 — 실측: 데스크톱 확장 상세 태그가 **0개**로 나와 버그로 볼 뻔했는데,
  `about:blank` 를 거쳐 새로 열자 **4개**였다. 조건을 바꿔 잴 때는 반드시 사이에 빈 페이지를 넣는다.
- 🔴 **`*{transition:none!important}` 은 CSS 전환만 끈다 — rAF 트윈은 안 끈다.**
  단계 전환은 `tweenTo()`(requestAnimationFrame)라서 이걸 넣어도 **중간 상태가 찍힌다.**
  실제로 `아주 멀리` 클릭 **직후** `#lands` transform 을 읽고 "far 배율 계산이 틀렸다"는
  **틀린 결론**을 냈다 — 트윈의 첫 동작이 `moveOnly(from)`(출발점으로 되돌림)이었다.
  단계·필터를 바꾸고 재는 진단은 **400ms 뒤에** 읽어야 한다.
- 🔴 **`*{transition:none!important}`을 항상 먼저 주입한다.** `--virtual-time-budget`이 CSS 전환을
  **중간에 얼린다.** 이걸 안 넣었을 때 상세 카드가 반투명하고 항로가 엉뚱한 데 그려진 것처럼 찍혀서
  **멀쩡한 걸 버그로 오진할 뻔했다.** 화면이 이상하면 렌더러를 의심하기 전에 전환부터 끈다.
- 찍은 PNG는 `SendUserFile`로 사용자에게 바로 보낸다. "못 봤다"보다 "찍어놨으니 봐달라"가 낫다.
- PIL이 없어 **크롭을 못 한다.** 작은 글씨를 봐야 하면 대상에 `transform:scale(2.4)`를 주입해 찍는다.
- ⚠️ 주입할 스텝을 **콤마로** 이어야 한다. 개행으로 이으면 배열이 깨져 스텝이 통째로 안 돈다 —
  화면0(출발지 선택)만 찍혀 나오는데 에러도 안 보여서 한참 못 알아챘다.

<details><summary><b>스크립트 전문</b> — 스크래치패드에 저장해 쓴다(저장소에 둘 자리가 없다)</summary>

```python
# -*- coding: utf-8 -*-
"""확인용 스크린샷 — 헤드리스 크롬으로 docs/index.html 을 굽는다.
빌드 파이프라인이 아니다. 사람이 눈으로 볼 PNG 를 만들 뿐이라 크론·배포와 무관하다."""
import io, os, subprocess, sys, pathlib
sys.stdout.reconfigure(encoding='utf-8')
ROOT = pathlib.Path(r"C:\Users\Ryu\Desktop\개인 프로젝트\galmal-frontend")
OUT  = pathlib.Path(sys.argv[1])
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
SRC = (ROOT / "docs/index.html").read_text(encoding="utf-8")

def inject(steps):
    js = ",".join(steps)
    return SRC.replace("</body>", "<script>(function(){var Q=[%s];var i=0;"
        "function go(){if(i>=Q.length)return;var f=Q[i++];try{f();}catch(e){console.log('SHOT-ERR',e.message);}setTimeout(go,450);}"
        "setTimeout(go,700);})();</script></body>" % js)

NOTRANS = ("function(){var st=document.createElement('style');"
           "st.textContent='*{transition:none!important;animation:none!important}';"
           "document.head.appendChild(st);}")
def pick(name):
    return ("function(){var g=document.querySelectorAll('#introMap g');for(var i=0;i<g.length;i++){"
            "var t=g[i].querySelector('text');if(t&&t.textContent.trim()==='%s'){"
            "g[i].dispatchEvent(new MouseEvent('click',{bubbles:true}));return;}}"
            "console.log('SHOT-ERR origin not found');}" % name)

def zoomdock():
    return ("function(){var d=document.getElementById('fdock');"
            "d.style.transform='scale(2.4)';d.style.transformOrigin='100% 100%';}")
def click(sel):
    return ("function(){var e=document.querySelector('%s');if(!e){console.log('SHOT-ERR no %s');return;}"
            "e.dispatchEvent(new MouseEvent('click',{bubbles:true}));}" % (sel, sel))

SHOTS = [
    ("1-home-1440",      1440, 900, [pick("서울")]),
    ("2-mood-culture",   1440, 900, [pick("서울"), click('.fchip.moodf[data-mood="문화"]')]),
    ("3-budget-50",      1440, 900, [pick("서울"), click('.fchip.budget[data-budget="500000"]')]),
    ("4-detail",         1440, 900, [pick("서울"), click('.fcard.hero')]),
    ("5-jeju",           1440, 900, [pick("제주")]),
    ("6-mobile-390",      390, 844, [pick("서울")]),
    ("7-tablet-900",      900, 800, [pick("서울")]),
    ("4b-detail-notrans", 1440, 900, [pick("서울"),
        "function(){var st=document.createElement('style');st.textContent='*{transition:none!important;animation:none!important}';document.head.appendChild(st);}",
        click('.fcard.hero')]),
    ("8-dock-zoom",      1440, 900, [pick("서울"), zoomdock()]),
    ("9-dock-zoom-50",   1440, 900, [pick("서울"), click('.fchip.budget[data-budget="500000"]'), zoomdock()]),
    ("10-dock-zoom-jeju",1440, 900, [pick("제주"), zoomdock()]),
]
tmp = ROOT / "docs/_shot.html"
try:
    for name, w, h, steps in SHOTS:
        tmp.write_text(inject([NOTRANS] + steps), encoding="utf-8")
        png = OUT / (name + ".png")
        r = subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
             "--force-device-scale-factor=2", "--screenshot=" + str(png),
             "--window-size=%d,%d" % (w, h), "--virtual-time-budget=9000",
             tmp.as_uri()], capture_output=True, text=True, errors="replace", timeout=120)
        err = "\n".join(l for l in (r.stderr or "").splitlines() if "SHOT-ERR" in l)
        ok = png.exists() and png.stat().st_size > 5000
        print("%-16s %s  %s  %s" % (name, "%dx%d" % (w, h),
              ("%.0fKB" % (png.stat().st_size/1024)) if png.exists() else "없음",
              "OK" if ok and not err else ("!! " + (err or "파일 없음/너무 작음"))))
finally:
    if tmp.exists(): tmp.unlink()
```

</details>

---

## 7. 세션 핸드오프 양식

챕터를 끝낸 세션은 마지막에 이 형식으로 남긴다.

```
## CHn 완료
- 한 것: (태스크별 1줄 + 커밋 해시)
- 안 고치고 남긴 것: BACKLOG.md #항목
- 다음 챕터 첫 태스크: (다음 세션이 바로 시작할 수 있게)
- 기획 세션에 전달: (스펙 미확정으로 막힌 것)
- 백엔드 세션에 전달: (CONTRACT 변경 요청)
```

---

## 8. 이전 직전 인수인계 (2026-09-08)

> 저장소를 `galmal-frontend`(프론트)·`galmal-backend`(백엔드)로 나누기로 사용자가 결정했다(기획 `SPLIT.md` `87ae866`).
> (처음 이름은 `galmal-web`·`galmal-api` 였다. 2026-09-11 사용자 결정으로 바꿨고 둘 다 빈 저장소로 만들어져 있다.)
> 이전이 시작되면 챕터 진행이 멈춘다. **재개할 사람이 알아야 할 것을 여기 남긴다.**

### 8-1. ~~🔴 먼저 처리할 것 — CH5 5커밋이 로컬에만 있다~~ → **해결(2026-09-08, `0dd68b7`)**

> 사용자 승인을 받아 `frontend` → `origin/frontend` → `origin/main`(fast-forward)로 올렸다.
> 아래는 무엇이 걸려 있었는지의 기록이다.
>
> ⚠️ **병합 중에 제휴 링크가 사라질 뻔했다.** `index.html` 충돌을 규칙대로 재빌드로 풀었는데,
> 로컬에 `TP_MARKER`가 없어 재빌드본이 **125건 전부에서 Aviasales(`ad:true`)를 빼먹었다.**
> §4 절차로 커밋본을 복원했다(검증 3종 통과). 백엔드가 **BB30**으로 받았다 — 막을 자리는
> 절차가 아니라 `build_site.py`이고, 마커 없이 도는 빌드를 경고 없이 통과시키는 게 결함이라는 판단이다.

`origin/frontend`가 `f1e70b9`(BE7) 시점에 멈춰 있었고, **CH5 T1~T5가 push되지 않았었다.**

```
7c3fd61 CH5 T5  펼친 필터 도크를 하단 시트로
814e169 CH5 T4  카드 태그 판정을 '사진 폭'으로
052cc99 CH5 T3  핀 탭은 상세를 안 연다
172db11 CH5 T2  모바일을 3단 시트로
09c56be CH5 T1  CDP 측정 도구 + B36 오진 정정
```

`origin/main`에도 없다(`git log origin/main..frontend` = 위 5개).
**이전 전에 push하고 main에 병합한다.** 안 하면 `SPLIT.md` M2 T5(동등성 증명)의
기준이 되는 "현 배포본"에 모바일 작업이 빠진 채로 증명이 성립해 버린다.

### 8-2. 챕터 상태

| 챕터 | 상태 | 비고 |
|---|---|---|
| CH0~CH4 | ✅ 완료·**push됨**(`origin/main`) | CH4 T7(지도가 핀으로 미끄러진다) 포함해 전부 끝 |
| CH5 | ✅ 완료·**push됨**(`0dd68b7`) | 8-1 |
| CH6 접근성·마감 | **미착수** | 8-3 |

기획 세션이 "CH4 T1~T6 push 대기 · T7 착수 여부 불명"으로 파악하고 있었으나
**CH4는 T7까지 끝나 `origin/main`에 있다.** 대기 중인 것은 CH5다.

### 8-3. CH6 — 🔴 **중단.** 이전이 끝난 뒤(M6 후) 재개한다

**사용자 지시(2026-09-08)**: *"일단 레포 나누는 거를 최우선으로 진행해 줘."*
기능 챕터를 전부 멈추고 이전을 단일 트랙으로 간다(기획 `0f5b638`).

**왜 이 순서가 맞나** — CH6 는 이전에 **해롭다.** 화면이 바뀌면 M2 T5 기준선을 다시 잡아야 하고,
기준선을 여러 번 다시 잡을수록 「같은 입력 → 같은 출력」 증명이 흐려진다(§8-8).
내가 먼저 「지금 CH6 를 시작하면 기준선이 또 흔들린다」고 짚었고, 기획이 「순서만 맞추면 된다」로
받았다가 사용자 지시로 정정됐다.

#### 재개할 때 그대로 쓸 수 있게 — 실측 현황 (2026-09-08)

| | 현재 | 뜻 |
|---|---|---|
| 필터 칩·정렬 | 전부 `<button>` | ✅ 이미 키보드로 닿는다. **할 일 없다** |
| 핀 | SVG `<g>`, `tabindex` 0건 | 🔴 Tab 으로 못 감 |
| 카드 | `<div class="fcard">` | 🔴 Tab 으로 못 감 |
| **focus 스타일** | **0건** | 🔴 Tab 을 눌러도 **어디 있는지 안 보인다** |
| Escape | 출발지 드롭다운만(`discover.js:1193`) | 🔴 상세·시트는 못 닫음 |
| 지도 | `role="img"` + `aria-label="여행지 발견 지도"` | 🔴 스크린리더엔 **그림 한 장**. 딜 125건이 안 읽힌다 |
| 자산 | js 91KB · css 28KB · d3 53KB · index 330KB, **런타임 요청 0** | ✅ 성능은 아마 할 게 없다 |

**제안했던 태스크(미승인)**: T1 카드·핀 Tab 이동 + Enter/Space · T2 focus 링 ·
T3 Escape 일관성 · T4 스크린리더용 딜 목록 · T5 성능 실측.

**로드맵에서 뺄 것 2개 (재개해도 유지)**
- **사진 정책 → 기획 소관.** 확인해 보니 **사진이 아예 없다.** 카드 사진 자리는 그라데이션(`c.g`)에
  「사진 준비중」이 얹혀 있다(`discover.js:649`). 「고칠 접근성」이 아니라 **「사진을 넣을 것인가」라는
  제품 결정**이고 이미지 라이선스가 걸린다. 프론트가 정할 게 아니다.
- **`<noscript>` → M2 로.** 지금 `<noscript>`에 노선 링크 36개는 있고 **딜 카드는 0개**다.
  그런데 노선 페이지는 M2 T2 에서 어차피 새로 짠다. 지금 고치면 **같은 곳을 두 번 짠다.**

#### ⚠️ CH4 T7 은 중단 대상이 아니다 — **이미 끝났다**

기획이 「CH4 T7(지도가 핀으로 미끄러진다) 착수 여부 불명, 이전 후 제일 먼저 돌아올 자리」로
파악하고 있으나 **사실이 아니다.** 커밋 `2969806` 으로 완료돼 `origin/main` 에 있고,
`viewForPin()`(`discover.js:753`) · `slideMs()`(`:766`) · `pinTarget()`(`:747`) 이 살아 있다.
**재개할 때 CH4 에서 할 일은 없다.** (기획에 전달함)

### 8-4. 미해결 백로그

- **B20**(핀 겹침) — 홍콩·선전·마카오가 `아주 멀리`에서 1~2px 안에 스택. 스펙이 "긴급하지 않다" 명시.
- **B35**(`.prompt` 첫 방문 한정 + 닫기) — 기획 확정(2026-09-04), 미착수.
- ⚠️ **B20 번호가 겹쳐 있다.** `BACKLOG.md:26`(핀 겹침)과 `:248`(네비 `노선별`이 링크가 아님, IA-1)이
  같은 번호다. 뒤엣것을 인용할 때는 반드시 `B20(IA-1)`로 쓴다. 다음에 백로그를 만질 때 재번호한다.

### 8-5. 재개 전제 — 없으면 확인 절차가 안 돈다

1. **`cdp.py`는 저장소에 없었다.** 스크래치패드(세션별 임시 폴더)에만 있어 이전 중에 사라진다.
   → 8-6에 전문을 박아 둔다. 재개하는 세션은 여기서 꺼내 쓴다.
2. **확인은 `git show HEAD:docs/data/deals.json` 기준으로 한다.** 작업 트리의 `deals.json`은
   빌드가 방금 덮어쓴 것이라 기준이 못 된다 (§4 「인라인 데이터를 커밋본으로 맞춘다」).
3. **기획이 실기기 확인을 요청해 둔 상태다.** 헤드리스 CDP는 Safari·안드로이드 크롬과 다르다.
   push 후 폰으로 봐야 닫히는 항목이다.
4. CH5에서 **스펙 없이 내가 판단한 것 2가지** — 재개 시 기획 확인이 필요할 수 있다.
   - 모바일은 **상시 라벨을 안 단다.** 배치 시도가 12/12·6/6 전부 실패해서, 활성 핀의 이름만
     `.plabel{font-size:20px}`로 띄운다.
   - `MOBILE` hero 태그 상한 2는 **당일 데이터로 실제로 걸리지 않았다.** 상한이 맞는지 미검증.

### 8-6. `cdp.py` 전문 (저장소에 자리가 없어 문서에 박는다)

§4의 `shot.py`는 데스크톱 전용이다. **모바일 폭은 반드시 이걸로 잰다** —
`--window-size=390`은 실제 뷰포트 489px를 준다(§4 🔴 항목).

<details><summary><b>cdp.py</b></summary>

```python
# -*- coding: utf-8 -*-
"""CDP 스크린샷 — 헤드리스 창은 최소 폭 ~500px 라 `--window-size` 로는 390px 모바일을 못 만든다.
`Emulation.setDeviceMetricsOverride` 로 **뷰포트를 직접 지정**한다.

표준 라이브러리만 쓴다(websocket 패키지 없음). 사용:
    from cdp import Chrome
    with Chrome() as c:
        c.shot(url, out_png, width=390, height=844, dsf=2, mobile=True, wait=2.5, js=None)
"""
import base64, hashlib, json, os, socket, struct, subprocess, sys, time, urllib.request

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"


class WS:
    def __init__(self, url):
        _, rest = url.split("://", 1)
        hostport, path = rest.split("/", 1)
        host, port = hostport.split(":")
        self.s = socket.create_connection((host, int(port)), timeout=30)
        key = base64.b64encode(os.urandom(16)).decode()
        self.s.sendall(("GET /%s HTTP/1.1\r\nHost: %s\r\nUpgrade: websocket\r\n"
                        "Connection: Upgrade\r\nSec-WebSocket-Key: %s\r\n"
                        "Sec-WebSocket-Version: 13\r\n\r\n" % (path, hostport, key)).encode())
        buf = b""
        while b"\r\n\r\n" not in buf:
            buf += self.s.recv(4096)
        acc = base64.b64encode(hashlib.sha1((key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode()).digest()).decode()
        assert acc.encode() in buf, "웹소켓 핸드셰이크 실패"
        self.buf = buf.split(b"\r\n\r\n", 1)[1]

    def _read(self, n):
        while len(self.buf) < n:
            d = self.s.recv(65536)
            if not d:
                raise IOError("연결 끊김")
            self.buf += d
        out, self.buf = self.buf[:n], self.buf[n:]
        return out

    def send(self, obj):
        p = json.dumps(obj).encode()
        n = len(p)
        h = b"\x81"
        if n < 126:      h += struct.pack("!B", n | 0x80)
        elif n < 65536:  h += struct.pack("!BH", 126 | 0x80, n)
        else:            h += struct.pack("!BQ", 127 | 0x80, n)
        m = os.urandom(4)
        self.s.sendall(h + m + bytes(b ^ m[i % 4] for i, b in enumerate(p)))

    def recv(self):
        while True:
            b1, b2 = self._read(2)
            op, ln = b1 & 0x0F, b2 & 0x7F
            if ln == 126:   ln = struct.unpack("!H", self._read(2))[0]
            elif ln == 127: ln = struct.unpack("!Q", self._read(8))[0]
            data = self._read(ln)
            if op == 1:
                return json.loads(data.decode())
            if op == 8:
                raise IOError("서버가 닫음")

    def close(self):
        try: self.s.close()
        except Exception: pass


class Chrome:
    def __init__(self, port=9333):
        self.port = port
        self.proc = subprocess.Popen(
            [CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--mute-audio",
             "--no-first-run", "--remote-debugging-port=%d" % port,
             "--user-data-dir=" + os.path.join(os.environ.get("TEMP", "."), "cdpprof%d" % port),
             "about:blank"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(80):
            try:
                urllib.request.urlopen("http://127.0.0.1:%d/json/version" % port, timeout=1).read()
                return
            except Exception:
                time.sleep(0.25)
        raise RuntimeError("크롬이 안 떴다")

    def __enter__(self): return self
    def __exit__(self, *a): self.close()

    def close(self):
        try: self.proc.terminate()
        except Exception: pass

    def shot(self, url, out, width=390, height=844, dsf=2, mobile=True, wait=2.5, js=None):
        req = urllib.request.Request("http://127.0.0.1:%d/json/new?%s" % (self.port, "about:blank"), method="PUT")
        tgt = json.loads(urllib.request.urlopen(req, timeout=10).read())
        ws = WS(tgt["webSocketDebuggerUrl"]); i = [0]
        def cmd(method, params=None):
            i[0] += 1
            ws.send({"id": i[0], "method": method, "params": params or {}})
            while True:
                m = ws.recv()
                if m.get("id") == i[0]:
                    if "error" in m: raise RuntimeError(method + ": " + json.dumps(m["error"], ensure_ascii=False))
                    return m.get("result", {})
        try:
            cmd("Page.enable"); cmd("Runtime.enable")
            cmd("Emulation.setDeviceMetricsOverride",
                {"width": width, "height": height, "deviceScaleFactor": dsf, "mobile": mobile})
            cmd("Page.navigate", {"url": url})
            time.sleep(wait)
            if js:
                cmd("Runtime.evaluate", {"expression": js, "awaitPromise": False})
                time.sleep(1.2)
            r = cmd("Page.captureScreenshot", {"format": "png"})
            open(out, "wb").write(base64.b64decode(r["data"]))
            v = cmd("Runtime.evaluate", {"expression":
                "document.documentElement.clientWidth+'x'+document.documentElement.clientHeight",
                "returnByValue": True})
            return v["result"]["value"]
        finally:
            ws.close()
            try: urllib.request.urlopen("http://127.0.0.1:%d/json/close/%s" % (self.port, tgt["id"]), timeout=5).read()
            except Exception: pass
```

</details>

### 8-7. 이전이 프론트 구역에 가져오는 것 (`SPLIT.md` M2 — 참고)

지금 프론트가 소유하지 **않는** 코드가 넘어온다. 착수 전에 규모를 알고 있어야 한다.

| 넘어오는 것 | 현 위치 | 갈 곳 | 크기 |
|---|---|---|---|
| 노선 페이지 36장 | `collector/build_site.py:191 route_page()` | `site/route.py` | 180줄 |
| 딜 카드 | `build_site.py:129 deal_card()` | 프론트 | 34줄 |
| 스파크라인 SVG | `build_site.py:100 sparkline()` | 프론트 | 29줄 |
| sitemap·robots | `build_site.py:384 build_seo()` | `site/seo.py` | 20줄 |
| `BASE_URL`·`SITE_NAME`·`OG_IMAGE`·소유확인 메타 | `collector/theme.py` | `site/shell.py` | — |

**경계 역행이 하나 있다**(실측): 프론트 소유 `collector/discover_home.py:9-10`이
백엔드 모듈 `labels`·`theme`를 import 한다. 이전 때 같이 풀린다.

데이터는 파일 경로가 아니라 URL로 받는다 — `https://api.galmal.kr/v1/deals.json` 외 3종.
지금 `discover.js`는 `window.__DEALS`(HTML 인라인)만 읽으므로 **JS는 안 바뀐다.**
바뀌는 건 그걸 인라인해 주는 빌드 쪽이다.

### 8-8. M2 T5 검수 전제 — 「이전은 옮기기만 한다」

> **결론이 한 번 뒤집혔다.** 처음엔 「diff 0은 성립하지 않는다(22/36 변화)」로 적었는데,
> 기획이 그 위에 규칙을 세워 **diff 0이 성립하게** 만들었다. 아래는 최종본이다.

#### 규칙 (기획 확정 2026-09-08, `e38a28b`)

> **이전 중에는 동작을 바꾸지 않는다.** 고칠 것은 **이전 전에** 현행 코드에서 고쳐
> 크론이 한 번 배포하게 하거나, **M3 이후에** 별도 챕터로 한다. 이전은 **옮기기만** 한다.

내가 「그게 이전이 깨뜨린 건지 의도한 개선인지 구분이 안 된다」고 보고한 게 규칙이 됐다.

#### 그래서 프론트가 **재현할** 현행 동작 3가지 (`CONTRACT.md` 표)

| 블록 | 현행 SQL | 프론트가 재현할 것 |
|---|---|---|
| `months` | `HAVING COUNT(*)>=3` | `n >= 3` |
| `months` | `ORDER BY m LIMIT 10` | **월 오름차순 앞에서 10개** |
| `airlines` | `ORDER BY MIN(price) LIMIT 8` | 최저가 오름차순 상위 8개 |

**`LIMIT 10`이 창인지 임계인지의 판정은 이전 후로 미룬다.** 지금 답은 「현행대로」다.

🔴 **`weekdays`에 `n >= 3`을 걸지 않는다.** 계약 초안에 있었으나 **기획 착오였고 빼갔다** —
현행 `weekday_min`에는 건수 필터가 없다. `length >= 2`만 건다. `n`은 계약에 남지만
이전 중엔 쓰지 않는다. (내가 `ICN-RMQ` 5→3을 실측해 잡았다. 타이중이다.)

#### 실측 기록 — 왜 이 규칙이 필요했나 (`data/prices.db`, 2026-09-08)

| 무엇을 바꾸나 | 변화 노선 | 늘어남 | 줄어듦 |
|---|---|---|---|
| `LIMIT 10`만 제거 | 15/36 | 15 | 0 |
| `HAVING COUNT(*)>=3`만 제거 | 5/36 | 5 | 0 |
| 둘 다 제거 (계약 M1 초안) | **22/36** | 22 | 0 |
| 위 + BB29 창 | 22/36 | 10 | **12** |

**내가 처음 낸 15/36은 불완전했다** — `LIMIT 10`만 빼고 쟀다. 백엔드가 정정했고
네 숫자 전부 재현했다. 재현만 하면 이 표의 변화는 **전부 0이 된다.**

#### 🔴 BB29 — 이전 전에 고쳐질 라이브 결함. 기준선이 여기서 바뀐다

`month_min`에 `depart_date` 창이 없어서 **지난 달 버킷이 살아 있다.**
배포본에서 직접 확인했다(오늘 2026-09-08):

```
ICN-GUM  ICN-HKG  ICN-LAX  ICN-NGO   "8월 출발이 가장 저렴합니다"
ICN-KUL                              "7월 출발이 가장 저렴합니다"
```

**5장이 살 수 없는 달에 떠나라고 쓰고 있다.** 임계로는 못 막는다 —
`ICN-NRT`의 2026-08 버킷은 915건이라 `n>=3`을 여유롭게 통과한다.
**내 임계는 얇은 것을 막지 낡은 것을 못 막는다. 다른 문제다.**

→ 백엔드가 **현행 코드에서** 창을 넣고 크론이 한 번 배포한다.
**그 화면이 M2 T5의 비교 기준**이다. M1은 그 뒤에 착수한다(사용자 승인 대기).

#### ✅ 기준선 준비됨 (2026-09-08, 백엔드 확인) — 그리고 방향이 다시 바뀌었다

BB29 수정이 라이브에 반영됐다. **지금 `galmal.kr`의 노선 페이지가 M2 T5 기준선이다.**
백엔드가 `curl`로 5장 전수 확인했고, 나도 `month_min`의 창과 산출물 36장을 확인했다
(지난 달 추천 0장).

🔴 **그래서 위 표의 「줄어듦 12」는 이제 해당 없다.** 그 감소분이 **기준선에 이미 반영됐다.**
M1 diff 는 **증가 방향만** 본다.

| 시점 | M1 적용 시 예상 diff |
|---|---|
| BB29 배포 **전** 기준선 | 22/36 (늘어남 10 · 줄어듦 12) ← 낡았다 |
| **BB29 배포 후 기준선(지금)** | **22/36, 전부 늘어남** |

`HAVING`·`LIMIT`은 백엔드가 **그대로 뒀다** — 「이전 중 동작 변경 금지」대로 결함만 고쳤다.
그래서 M1 에서 두 필터를 빼는 계획과 내 실측은 그대로 유효하다.

⚠️ **검수 당일에 기준선을 다시 받는다.** 크론이 매일 `docs/`를 다시 만들어서 며칠 지나면
숫자가 또 달라진다. diff 대조는 **같은 날 받은 기준선끼리** 해야 한다.

#### 🔴 BB31 — `fmt_month`가 연도를 버린다. M1 이 `LIMIT 10`을 빼는 순간 터진다

`labels.py:71`이 `'2027-02' → '2월'`로 **연도를 버린다.** 지금 화면의 `ICN-LAX` "2월",
`ICN-KUL` "6월"이 실제로는 **2027년**이다.

**지금은 안 헷갈린다** — 창 덕에 미래만 남으니 "2월"은 다음에 오는 2월로 유일하게 읽히고,
`LIMIT 10`이 12개월을 못 넘게 막고 있어 같은 월 이름이 두 번 나오지 않는다.

🔴 **M1 이 `LIMIT 10`을 빼면 깨진다.** 버킷이 **13개**가 되는 순간 `"9월"`이 2026·2027 둘을
가리키고 **막대 두 개가 같은 이름**을 단다.

실측(2026-09-08, 창 적용 · 두 필터 제거 가정):

```
ICN-DPS  ICN-CDG  ICN-LHR  ICN-SYD   12개  (2026-09 ~ 2027-08)
ICN-JFK                              11개
최대 12개 — 여유 정확히 1개. 오늘은 중복 0건.
```

**터질 조건은 「데이터가 쌓이는 것」이 아니라 「항공사가 13번째 달을 여는 것」이다.**
창이 `depart_date >= 오늘`이라 판매 지평(약 12개월)을 따라 앞으로 미끄러지므로 보통 12에서
멈춘다. 양 끝이 부분 달로 걸리면 13이 된다.

→ 표시 문자열이라 `COPY.md` 소관이고 이전하면 **프론트가 만든다.**
백엔드가 기획에 판정을 요청해뒀다. **M1 착수 전에 결론이 나야 M2 에서 두 번 안 고친다.**
연도를 언제 붙일지(항상 / 해가 바뀔 때만 / 첫 막대에만)는 화면 판단이라 기획 결정을 기다린다.

#### 검수할 때 지킬 것

1. **기준선을 확인하고 시작한다** — BB29 수정이 배포된 뒤의 화면인가.
   수정 전 화면과 비교하면 5장이 통째로 달라 보인다.
2. 그 기준선에 대해 **`months`·`weekdays`·`airlines` 전부 diff 0**이어야 한다.
   한 장이라도 막대 수가 다르면 재현 규칙(위 표)을 잘못 짠 것이다.
3. **테스트 통과는 화면이 멀쩡하다는 증거가 아니다**(§4). 렌더 스크린샷을 같이 낸다.

#### 창은 백엔드, 임계는 프론트 — 겹치지 않게

받은 `months`는 **이미 창으로 잘려 있다.** 프론트가 날짜로 다시 거르지 않는다 —
창이 두 곳에 생기면 갈라진다. 프론트가 거는 건 `n >= 3`과 `length >= 2`뿐이다.

### 8-9. 🔴 구독 `mailto:`는 파생이 아니라 **전선 규약**이다 — 형식을 바꾸면 조용히 반대로 동작한다

`CONTRACT.md`가 바뀌었다(백엔드 발견, 기획 반영). 노선 페이지의 구독 버튼이 만드는
`mailto:`의 **주소·제목·본문 노선 표기**는 프론트가 지어내는 문장이 아니라
**IMAP 파서가 실제로 읽는 규약**이다. `meta.json`의 `subscribe` 블록에서 받는다.

⚠️ **틀리면 실패하지 않고 반대로 동작한다.** `_extract_route()`가 `None`을 반환하면
`load_subscribers()`가 `route or "ALL"`로 받는다 — **본문 형식을 바꾸면 구독 실패가 아니라
「전 노선 구독」이 된다.** 도쿄만 신청한 사람이 36노선 메일을 받는다.

**따라서 M2에서 노선 페이지를 옮길 때 `mailto:` 문자열을 "정리"하지 않는다.**
문구(「아래 버튼을 누르면…」·해지 안내)는 `COPY.md`가 정본이고 자유롭게 다루지만,
**주소·제목·본문의 노선 표기는 규약이라 손대지 않는다.**

### 8-10. 확정된 자잘한 것들 (기획 `e38a28b` 반영)

- **`dateModified`는 `generated` 기준.** 빌드 시각이 아니라 **데이터 생성 시각**이다 —
  페이지가 주장하는 건 "이 데이터가 언제 것인가"다. 기획이 `CONTRACT.md` 파생 목록에 명시했다.
- **`charts.py`는 프론트로 온다.** `SPLIT.md` 표에 추가됐다. `send_alerts.py`가 안 쓰는 걸
  확인해서 「옮겨도 알림 메일이 안 깨진다」는 근거가 됐다.
- **`tests/test_charts.py`도 프론트로.** M4 T4가 «`tests/` 이동, 단 `test_charts.py` 제외»로 바뀌었다.
- **`deal_card()`·`sparkline()` 63줄은 옮기지 않는다.** 죽은 코드라 M3에서 지운다.
  (`sparkline`이 `is_direct` 축을 쓰는데 계약 `trend`엔 그 축이 없다 — 살아 있었으면 M2에서 막혔다.)
- **`labels.py`는 쪼갠다.** 참조(`city`·`airline_name`·`region_of`)는 백엔드,
  포맷(`fmt_date`·`fmt_month`·`SQL_WEEKDAY`)은 프론트.
- **`TP_MARKER` 없는 재빌드**는 M2·M3에서 다시 만난다(§8-1). 백엔드가 **BB30**으로 받았다 —
  막을 자리는 절차가 아니라 `build_site.py`라는 판단이다.
### 8-11. ✅ M2 완료 (2026-09-09, `94477f9`) — 동등성 39/39

기준선 **`05d0de9`** 대비 **바이트 동일 39/39**. 픽스처(입력)와 비교 대상(출력)을
같은 커밋에서 가져왔으므로 「같은 입력 → 같은 출력」이 구조적으로 보장된다.

| 태스크 | 만든 것 | 근거 |
|---|---|---|
| T1 | `fixtures/v1/` 39 + `capture.py` + `README.md` | 기준선과 바이트 동일 39/39 |
| T2 | `site/shell.py` ← `theme.py` | **AST 동일**(독스트링만 다름) |
| T3 | `site/charts.py` ← `charts.py` | AST 동일 |
| T4 | `site/fmt.py` ← `labels.py` 포맷부 | 실데이터 113건 문자열 대조 불일치 0 |
| T5 | `site/route.py` + `build.py` | 노선 36/36 바이트 동일 |
| T6 | `site/seo.py` | sitemap·robots 동일 |
| T7 | `site/home.py` ← `discover_home.py` | `index.html` 동일 + 렌더 확인 |

**홈 렌더 확인**(노선과 달리 JS 가 그리므로 필요했다): 핀 24 · 카드 24 · 딜 125 ·
origins 4 · **콘솔 에러 0건**. 자산 404 는 HTML 에 안 나타나므로 콘솔을 같이 봤다.

**경계 검사**: `site/` 가 `collector/` 를 import 하는 곳 **0건**, sqlite 실사용 **0건**.

#### 🔴 diff 0 이지만 무변경은 아니다 — 잠복 **변경** 하나 + 잠복 **부채** 하나

> 처음엔 잠복 변경이 둘(BB28 · `dateModified`)이었다. `dateModified` 는 **잠복 변경이 아니라
> 버그였고**(2026-09-11 발견, `b471d0d` 로 수정) 이제 새 경로와 옛 경로가 매일 같은 날짜를 낸다.
> 경위는 아래 표의 취소선 행.

기획이 범주를 갈랐다(2026-09-09). 내가 셋을 「잠복 변경」으로 뭉쳐 적었는데 **틀렸다** —
필요한 것이 다르다:

| | 잠복 **변경** | 잠복 **부채** |
|---|---|---|
| 무엇 | 오늘 바이트는 같은데 **나중에 동작이 갈린다** | 오늘 바이트를 **같게 만들려고** 넣은 임시 코드 |
| 예 | BB28 | **`inline_deals()`** |
| 적어야 할 것 | **갈리는 조건** | **없앨 조건** |
| 위험 | 그날 회귀로 오인된다 | 아무도 안 지워서 영구화된다 |

그래서 어댑터는 「이전 중 동작 변경 금지」 위반이 아니다 —
**규칙을 지키려고 치른 값**이다. 조건 셋은 *동작을 바꾸는 것*에 거는 문이지
*동작을 유지하려고 넣은 코드*에 거는 게 아니다.


| 무엇 | 왜 오늘 안 보이나 | 언제 갈리나 |
|---|---|---|
| **BB28** — 임계를 문장에도 (`usable()`) | 36노선 중 버킷 2개 미만이 `months` 0 · `weekdays` 0 | **새 노선이 들어오는 날.** 그때 「언제 가면 싼가」가 사라지는 게 **정상** |
| ~~**`dateModified`·`lastmod`** `today_utc()` → `generated[:10]`~~ | ~~오늘 둘 다 같은 날짜~~ | ~~크론이 UTC 자정 근처로 옮겨갈 때. 그때 `generated` 쪽이 옳다~~ → **🔴 버그였다. 아래 「dateModified 경위」** |
| **`home.inline_deals()`** — v1 봉투를 현행 모양으로 되돌림 | 의도적으로 바이트를 맞춘 것 | 아래 |

**`inline_deals()` 는 이전용 어댑터다. 영구 코드가 아니다.**
`discover.js` 는 `deals`·`origins` 만 읽고 `updated` 는 **안 읽는다**
(실측 `D.deals` 7 · `D.origins` 12 · `D.updated` **0**). 그래서 v1 봉투를 그대로 박아도
화면은 똑같이 돈다. 그런데도 되돌린 이유는 **증명을 흐리지 않기 위해서다** —
봉투만 바꿔도 `index.html` 이 크게 diff 나고, 그러면 「그래도 화면은 같다」를 사람이
눈으로 판정해야 한다. 바이트가 같으면 판정할 게 없다.
**없앨 조건**: M6 후 `discover.js` 가 `generated` 를 직접 읽게 되면 지운다.

#### ⚠️ M2 가 안 한 것 — 다음 단계가 해야 한다

1. **빌드가 `assets/`·`data/` 를 안 내보낸다.** 지금은 `docs/` 에 이미 있어서 도는 것이고,
   분리된 저장소에서는 **M4 가 자산을 옮겨야** 성립한다. `world.geojson` 도 같이 간다
   (커밋 2회짜리 정적 자산이라 API 가 아니라 파일로 받는다 — `--world`).
2. **옛 코드를 안 지웠다.** `collector/` 원본 5개 그대로이고 크론도 옛 것을 부른다.
   **지금 사이트는 아무것도 안 바뀌었다** — 두 벌이 나란히 있을 뿐이다. 스위치는 M3(백엔드).

#### 🔴 M4 에서 또 대조할 때 — 「전부 다르다」가 나오면 먼저 줄바꿈을 의심한다

백엔드가 M2 결과를 독립 검증하다 처음에 **39/39 전부 「다름」**을 봤다. 내용이 아니라
**줄바꿈**이었다. 이 저장소는 `core.autocrlf=true` 라(실측 2026-09-09):

| 어디 | 줄바꿈 |
|---|---|
| **작업 트리**의 `docs/*.html` | **CRLF** (체크아웃 때 git 이 변환) |
| **git 안의 원본**(`git show <SHA>:…`) | **LF** |
| 갓 생성한 파일 | **LF** |

실측: `docs/routes/ICN-FUK.html` — 작업 트리 CRLF 352 · LF 0 / `git show` CRLF 0 · LF 352.

**내 M2 대조가 통과한 건 `git show` 로 읽었기 때문이다.** 작업 트리 파일과 비교했으면
전부 다르게 나왔다. `git status` 는 **깨끗한데** `cmp` 만 다르게 보이므로
**눈으로는 설명이 안 된다** — 내용 차이로 오인해 되돌리면 멀쩡한 이전을 뒤집는다.

**규칙**: 산출물 대조는 **항상 `git show <SHA>:<경로>` 기준**으로 한다.
어쩔 수 없이 작업 트리와 비교해야 하면 줄바꿈을 지우고 비교한다:

```bash
cmp -s <(tr -d '\r' < a) <(tr -d '\r' < b)
```

§4 의 「작업 트리의 `deals.json` 을 커밋본이라고 읽지 말 것」과 **같은 부류**다 —
이유는 다르지만(그건 재빌드가 덮어써서, 이건 줄바꿈 변환) 결론이 같다:
**비교의 기준은 언제나 git 안의 것이다.**

#### 🔴 dateModified 경위 — 잠복 변경으로 적었는데 버그였다 (2026-09-11)

`site/route.py`·`build.py` 가 `meta["generated"][:10]` 을 썼다. `generated` 는 `now_kst()` 로 찍힌
**KST 시각**이라 앞 10자는 **KST 날짜**다. 그런데 **`CONTRACT.md:603` 은 처음부터
「`generated` 의 UTC 날짜」라고 적고 있었다**(`e38a28b`, M2 착수 전). BB17 도 기계용 날짜는 UTC 다.
**나는 계약의 그 줄을 읽고 「데이터 생성 시각」만 반영하고 「UTC」를 빠뜨렸다.**

틀린 판단이 둘 겹쳤다:
1. **구현** — 계약 603줄을 반만 구현했다.
2. **빈도** — 「크론이 UTC 자정 근처로 **옮겨가면** 갈린다」고 적었는데 크론은 **이미 거기 있었다.**
   22:10 UTC 예약이지만 GitHub 지연으로 **UTC 자정 앞뒤로 반반** 돈다
   (`gh run list` 최근 8회: 자정 전 23:46·23:47·23:57·23:58 / 후 00:01·00:05·00:06·00:13).
   v1 이 생긴 뒤 4회가 우연히 전부 자정 후라 아무도 못 봤다.
   **조건은 맞게 짚었고 그 조건이 지금 얼마나 자주 켜지는지는 안 쟀다.**
   `gh run list` 한 번이면 됐다.

M3 T1 이 매일 두 경로를 대조하기 시작해서 드러났다. 수정 없이 뒀으면 **자정 전 날마다
노선 36장 + sitemap 이 날짜 한 줄씩 달라** 잡이 실패했을 것이다. 사이트는 옛 산출물이
나가 멀쩡하지만, 이틀에 한 번 실패가 뜨면 **진짜 차이가 섞여도 못 가린다.**

**수정**(`b471d0d`): `machine_date()` — 생성 시각을 UTC 로 바꾼 뒤 날짜를 뽑는다.
기준선 39/39 · 오늘 main 산출물 39/39 · 자정 전 흉내에서 옛 경로와 같은 날짜.
`home.py` 의 `[:16]` 은 **화면 표시용 갱신 시각**이라 KST 가 맞고 옛 경로도 같다 — 안 건드렸다.

#### 계약 검증 결과 — 「계약만 읽고 만들 수 있는가」

**만들 수 있었다. 실물을 보고 추측한 필드는 0개다. 다만 계약에 적힌 한 줄을 틀리게 구현했다**
(`dateModified` — 바로 위 경위). 처음엔 「추측한 필드 0개」만 적어 **계약을 온전히 지킨 것처럼**
읽혔는데, 지어낸 것이 없다는 것과 적힌 대로 만들었다는 것은 다르다.

계약에 없었으면 조용히 틀렸을 자리 셋:

- `wd` 가 `0=일요일`이고 **순서를 믿지 말라**는 명시 → `weekday_name()` 을 따로 만들었다
- `n` 이 **버킷 안의 건수**지 배열 길이가 아니라는 구분
- 구독 `mailto:` 가 **표시가 아니라 전선 규약**이라는 것 — 명시가 없었으면
  URL 인코딩을 「정리」했을 것이고, **그 결과가 diff 0 도 통과했을 것이다**(HTML 은 같아 보인다).
  며칠 뒤 「도쿄만 신청한 사람이 36노선 메일을 받는」 걸로 나타났을 자리다.

#### 다음

**M3(백엔드)** — 크론을 새 코드로 돌리고 옛 HTML 생성부를 지운다. 사용자 승인 별도.
프론트가 M3 에서 할 일은 없다. M4(레포 분할)에서 `site/` `fixtures/` `assets/` 를 옮긴다.

### 8-12. ⏸ 이전 보류 (2026-09-09, 사용자) — 재개 지점과 M4 에서 프론트가 할 일

**사용자 지시**: *"해야 할 일 정리해 놓고 좀 미뤄야 할 듯. 먼저 해야 할 일이 있음."*
M2 가 끝난 자리에서 멈춘다. M3(백엔드) 미승인, M4 는 그 뒤다.

#### 지금 상태 — 무기한 방치해도 안 깨진다

```
기준선 05d0de9 대비  39/39 바이트 동일  (프론트·백엔드·기획 각각 독립 검증)
크론                옛 경로(build_site.py) 그대로 — 스위치 안 함
산출물              옛 HTML 36장 + 새 v1 39개가 나란히
사이트              평소와 동일
```

**여기까지 한 일은 전부 「더하기」다.** `site/` 가 생겼을 뿐 지운 게 없고,
크론은 아직 `site/build.py` 를 안 부른다.

#### 🔴 보류 중에는 프론트 구역을 잠근다

**`site/` 도 `docs/assets/discover.js|css` 도 건드리지 않는다.** 이유가 둘이다:

1. **39/39 는 지금 코드에 대한 증명이다.** 보류 중에 `site/` 가 바뀌면 M3 스위치 때 다시 증명해야 한다.
2. **`discover.js` 가 바뀌면 `index.html` 이 바뀐다.** 그러면 M3 에서
   「스위치가 깨뜨렸나, 우리가 바꿨나」를 못 가린다.

CH6 는 이미 중단(§8-3)이므로 새로 지킬 것은 없다. 잠긴 상태로 두면 된다.

#### M4 에서 프론트가 할 일 (`SPLIT.md` M4 T5)

`galmal-frontend` 저장소로 옮긴다(옛 이름 `galmal-web`):

| 옮길 것 | 비고 |
|---|---|
| `site/` | 빌드 진입점·화면 코드 7파일 |
| `fixtures/` | v1 사본 39 + `capture.py` + `README.md` |
| `docs/assets/` | `discover.js|css` · `d3-geo` · `d3-array` · `og.png` |
| `docs/data/world.geojson` | **정적 자산**이다. API 가 아니라 파일로 받는다(`--world`) |
| `.github/workflows/deploy.yml` | 신설. 백엔드 크론이 `repository_dispatch` 로 깨운다 |

**🔴 M2 에서 실측으로 알게 된 함정 셋 — M4 가 정확히 이걸 밟는다**

1. **`site/build.py` 는 `assets/` 를 안 내보낸다.**
   `index.html` · `routes/` · `sitemap.xml` · `robots.txt` 만 쓴다. 지금은 `docs/` 에
   이미 있어서 도는 것이다. **새 저장소에 자산을 안 옮기면 HTML 은 멀쩡한데 화면만 백지가 된다.**
   HTML diff 로는 절대 안 잡힌다 — **자산 404 는 HTML 에 안 나타난다.**
   그래서 M4 확인에는 **반드시 브라우저 콘솔 에러 0건**을 넣는다(M2 홈 확인에서 쓴 방법).
2. **`docs/` 를 비우고 다시 만들지 않는다.**
   `assets/` · `world.geojson` · **`CNAME`** 이 날아간다. `CNAME` 이 날아가면
   **커스텀 도메인이 풀린다.** 현행 `build_site.py` 가 `docs/` 를 안 지우고 덮어쓰기만
   하는 이유가 이것이다 — 새 `deploy.yml` 도 같은 규칙을 지킨다.
3. **대조는 `git show <SHA>:<경로>` 로 한다.** 작업 트리와 비교하면 줄바꿈 때문에
   **전부 다르게 나온다**(§8-11 CRLF 항목). 세 세션이 전부 한 번씩 걸렸다.

#### ✅ M4 T0 — `galmal-frontend` 보안 설정 끝남 (2026-09-11, 사용자 승인)

빈 저장소 상태에서 `SPLIT.md` §M4 T0 기준으로 걸었다. `gh api` 재조회 20/20 일치.

| 설정 | 값 |
|---|---|
| Actions | **GitHub 이 만든 것만**(`selected` · `github_owned_allowed`) — M4 배포 액션 5종이 전부 해당 |
| 외부 기여자 PR 워크플로 | `all_external_contributors` 승인 필요 |
| `main` | ruleset `main-protection`(id `22933079`) — **삭제 금지 · 강제 push 금지**, 우회 0명 |
| Dependabot 경보 · 비공개 취약점 신고 | 켬 |
| 위키 · 프로젝트 | 끔 (이슈는 둠) |
| 기본값으로 이미 켜져 있던 것 | 비밀 스캐닝 · 푸시 차단 · 토큰 `read` · Actions PR 승인 불가 |

`main` 보호를 branch protection 이 아니라 **ruleset** 으로 건 이유: 빈 저장소엔 `main` 이 없어
branch protection 을 못 건다. ruleset 은 이름에 걸려서 첫 push 부터 적용된다.
**M4 첫 push 는 일반 push 라 안 막힌다**(`creation` 규칙은 안 걸었다). 강제 push 는 소유자도 막힌다.

#### 재개 절차 (`SPLIT.md` 맨 앞)

```
1. 세 세션 pull
2. 건강 확인 — 딜 수 == 제휴 링크 수 · v1 39개 · BB29 유지(지난 달 추천 0장)
3. M3(백엔드) 승인 → 완료 → 그다음이 M4(프론트 차례)
4. 기준선 05d0de9 는 다시 안 잡아도 된다 — M2 증명이 이미 끝났다
```

#### 재개해도 안 나빠지는 것

- **기준선은 SHA** 라 날짜가 넘어가도 무관하다(2026-09-09 크론이 돌았어도 그대로였다)
- **CH6 실측 현황**(§8-3 — `focus` 스타일 0건 등)은 남겨뒀다. 다시 안 재도 된다
- **계약 §v1** 은 양쪽이 실물로 증명했다
- **`cdp.py`** 전문이 §8-6 에 있다. 스크래치패드가 날아가도 복구된다
