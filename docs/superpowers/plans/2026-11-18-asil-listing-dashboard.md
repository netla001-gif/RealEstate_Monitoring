# 아실 매물증감 대시보드 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 아실 비공식 API로 전국 시/도·구/군 매매·전세·월세 매물 수를 매일 CSV에 쌓고, 정적 페이지로 일/주/월 증감률을 보여준다.

**Architecture:** `collect.py`(stdlib만 사용)가 지역 목록 조회 → 지역별 시계열 수집 → `data/listings.csv` upsert. GitHub Actions가 매일 실행·커밋. `index.html`이 CSV를 fetch해 히트맵/순위표/추이 차트 렌더, GitHub Pages로 배포.

**Tech Stack:** Python 3.12 stdlib (urllib, csv, re, json), GitHub Actions, 바닐라 JS + Chart.js 4.4.1 (cdnjs).

**Spec:** `docs/superpowers/specs/2026-11-18-asil-listing-dashboard-design.md`

## Global Constraints

- 외부 의존성 없음 (Python은 stdlib만, 프론트는 Chart.js CDN 하나).
- 요청 간 1초 대기. User-Agent `Mozilla/5.0`, Referer `https://asil.kr/app/offer_sum_chart.jsp`.
- 최초 수집 시작일 2023-11-01. 이후 매일은 지난달 1일~오늘.
- CSV 컬럼: `date,code,name,level,sale,jeonse,wolse` (date=`YYYY-MM-DD`, level=`sido`|`sigungu`), (date, code) 기준 정렬·유일.
- 스케줄: 매일 KST 07:00 (`cron: '0 22 * * *'` UTC) + `workflow_dispatch`.
- 사용자 대상 문구는 한국어.

## Review Focus

1. 아실이 빈 응답/차단 응답을 줄 때 → 기존 CSV가 지워지지 않아야 함 (해당 지역은 건너뜀).
2. 한 지역 요청이 실패(타임아웃·HTTP 오류)해도 나머지 지역은 계속 수집.
3. 숫자에 쉼표(`"12,288"`), 연도 2자리(`26/11/18`) → 정수·`2026-11-18`로 정규화.
4. 비교 시점 매물 수가 0 → 증감률은 `–` 표시 (0 나누기/Infinity 금지).
5. 비교 날짜에 데이터가 없음(수집 누락일) → 그 날짜 이전의 가장 가까운 날짜 값 사용.

---

### Task 1: 수집기 `collect.py`

**Files:**
- Create: `collect.py`
- Test: `test_collect.py` (assert 기반, `python test_collect.py`로 실행)

**Interfaces:**
- Produces:
  - `parse_series(js: str) -> list[dict]` — `listData[i]={...}` 추출 → `{"date","sale","jeonse","wolse"}` (VM/VJ/VW).
  - `parse_regions(json_text: str, level: str) -> list[dict]` — `data_deal_count` JSON → `{"code","name","level"}`.
  - `merge(old: list[dict], new: list[dict]) -> list[dict]` — (date, code) upsert, 정렬된 결과.
  - `main()` — CSV 없으면 2023-11-01부터, 있으면 지난달 1일부터 수집 → merge → 저장.
- URL:
  - 시/도: `https://asil.kr/app/data/data_deal_count.jsp?mode=0&area=&today=0&yyyymm=0&deal=1&order=2&daily=false`
  - 구/군: 같은 URL에 `mode=1&area=<시도코드>`
  - 시계열: `https://asil.kr/app/data/data_offer_sum.jsp?apt=&area=<code>&c_apt=&c_area=&c_apt2=&c_area2=&deal=1&mode=2&sSize=&eSize=&sY=<Y>&sM=<M>&eY=<Y>&eM=<M>`

- [ ] **Step 1: 실패 테스트 작성**

```python
from collect import parse_series, parse_regions, merge
js = 'chartData[0]={"Date":"23/11/1","VM":6935};listData[1]={"Date":"23/11/01","VM":6935,"VJ":8040,"VW":6543,"gVM":""};listData[0]={"Date":"26/11/18","VM":12288,"VJ":4437,"VW":4660};'
assert parse_series(js) == [
    {"date": "2023-11-01", "sale": 6935, "jeonse": 8040, "wolse": 6543},
    {"date": "2026-11-18", "sale": 12288, "jeonse": 4437, "wolse": 4660}]
assert parse_series("chartData.length = 0;") == []
r = parse_regions('[{"idx":"1","area":"11680","areaname":"서울 강남구","total":"12,288","value":"12,293","rate":"-0.1"}]', "sigungu")
assert r == [{"code": "11680", "name": "서울 강남구", "level": "sigungu"}]
old = [{"date": "2026-11-17", "code": "11", "sale": 1}, {"date": "2026-11-18", "code": "11", "sale": 2}]
new = [{"date": "2026-11-18", "code": "11", "sale": 3}, {"date": "2026-11-19", "code": "11", "sale": 4}]
assert [x["sale"] for x in merge(old, new)] == [1, 3, 4]
assert merge(old, []) == old
print("ok")
```

- [ ] **Step 2: 실행 → 실패 확인** — `python test_collect.py` → `ModuleNotFoundError: collect`
- [ ] **Step 3: `collect.py` 구현** — 위 시그니처. `main()`은 지역별 try/except로 실패 시 경고 출력 후 계속, 응답 행 0개면 건너뜀. 응답은 `decode('utf-8', 'replace')`.
- [ ] **Step 4: 테스트 통과 확인** — `python test_collect.py` → `ok`
- [ ] **Step 5: 실제 최초 수집** — `python collect.py` → `data/listings.csv` 생성, 지역 수 ≈ 270, 행 수 ≈ 270×1,064. `grep -c ',11680,' data/listings.csv` > 1000.
- [ ] **Step 6: 커밋** (`collect.py test_collect.py data/listings.csv`)

### Task 2: GitHub Actions 워크플로

**Files:**
- Create: `.github/workflows/collect.yml`

**Interfaces:**
- Consumes: `python collect.py`, `python test_collect.py`

- [ ] **Step 1: 워크플로 작성** — `schedule: cron '0 22 * * *'` + `workflow_dispatch`, `permissions: contents: write`, setup-python 3.12, 테스트 → 수집 → `data/` 변경 시에만 `github-actions[bot]`로 커밋·푸시.
- [ ] **Step 2: 커밋 후 main 푸시, `gh workflow run collect.yml` → `gh run watch` 성공 확인.**
- [ ] **Step 3: 테스트 브랜치 삭제** — `git push origin --delete spike/actions-access`

### Task 3: 대시보드 `index.html` + Pages 배포

**Files:**
- Create: `index.html`

**Interfaces:**
- Consumes: `data/listings.csv` (Global Constraints의 컬럼)

- [ ] **Step 1: `index.html` 작성**
  - CSV fetch → 파싱. 기간 토글 일(1)/주(7)/월(30)일.
  - `rate(code, kind, days)`: 최신일 값 / (최신일−days 이하 가장 가까운 날짜 값) − 1, 기준값 0이거나 없으면 `null` → `–`.
  - 상단: 시/도 × 매매·전세·월세 히트맵 표 (증가=빨강, 감소=파랑, 강도는 |rate|).
  - 시/도 행 클릭 → 해당 시/도 코드 앞 2자리로 구/군 필터한 순위표 (열 클릭 정렬).
  - 지역 클릭 → Chart.js 라인 차트 (매매·전세·월세 3선, 전체 기간).
  - 라이트/다크 모드, 모바일 폭 대응, 최신 수집일 표시.
- [ ] **Step 2: 로컬 확인** — `python -m http.server` 후 브라우저에서 히트맵·순위표·차트 동작, 콘솔 오류 없음.
- [ ] **Step 3: 커밋·main 푸시, Pages 활성화** — `gh api repos/netla001-gif/RealEstate_Monitoring/pages -X POST -f source[branch]=main -f source[path]=/` → `https://netla001-gif.github.io/RealEstate_Monitoring/` 접속 확인.
