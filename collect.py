"""아실(asil.kr) 시/도·구/군 매매·전세·월세 매물 수를 data/listings.csv 에 쌓는다."""
import csv
import json
import os
import re
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone

CSV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "listings.csv")
FIELDS = ["date", "code", "name", "level", "sale", "jeonse", "wolse"]
START = (2023, 11)
REGION_PAGE = "https://asil.kr/app/deal_count.jsp?os=pc&area=11"
REGION_URL = ("https://asil.kr/app/data/data_deal_count.jsp?mode={mode}&area={area}"
              "&today={today}&yyyymm={cmp}&deal=1&order=2&daily=true")
SERIES_URL = ("https://asil.kr/app/data/data_offer_sum.jsp?apt=&area={code}&c_apt=&c_area=&c_apt2=&c_area2="
              "&deal=1&mode=2&sSize=&eSize=&sY={sy}&sM={sm}&eY={ey}&eM={em}")
HEADERS = {"User-Agent": "Mozilla/5.0", "Referer": "https://asil.kr/app/offer_sum_chart.jsp"}
LIST_RE = re.compile(r"listData\[\d+\]=(\{.*?\});")


def _int(v):
    return int(str(v or 0).replace(",", "") or 0)


def parse_series(js):
    rows = []
    for m in LIST_RE.finditer(js):
        d = json.loads(m.group(1))
        y, mo, day = d["Date"].split("/")
        rows.append({"date": f"20{y}-{int(mo):02d}-{int(day):02d}",
                     "sale": _int(d.get("VM")), "jeonse": _int(d.get("VJ")), "wolse": _int(d.get("VW"))})
    return sorted(rows, key=lambda r: r["date"])


def parse_regions(json_text, level):
    return [{"code": x["area"], "name": x["areaname"], "level": level} for x in json.loads(json_text)]


def parse_region_dates(html):
    """매물증감 페이지에서 (기준일, 첫 비교일)을 뽑는다. 둘 다 아실에 실제 있는 날짜여야 목록이 나온다."""
    today = re.search(r"var today = daily \? (\d{8})", html).group(1)
    cmp = re.search(r'<option value="(\d{8})">', html).group(1)
    return today, cmp


def merge(old, new):
    rows = {(r["code"], r["date"]): r for r in old}
    rows.update({(r["code"], r["date"]): r for r in new})
    return [rows[k] for k in sorted(rows)]


def fetch(url):
    time.sleep(1)  # 아실 부하/차단 방지
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8", "replace")


def main():
    now = datetime.now(timezone(timedelta(hours=9)))  # 아실은 KST 기준
    old = []
    if os.path.exists(CSV_PATH):
        with open(CSV_PATH, newline="", encoding="utf-8") as f:
            old = list(csv.DictReader(f))
    prev = now.replace(day=1) - timedelta(days=1)
    have = {r["code"] for r in old}  # 이력이 없는 지역(최초·신규·이전 실패)은 처음부터 받는다

    today, cmp = parse_region_dates(fetch(REGION_PAGE))
    regions = parse_regions(fetch(REGION_URL.format(mode=0, area="", today=today, cmp=cmp)), "sido")
    for sido in list(regions):
        try:
            regions += parse_regions(fetch(REGION_URL.format(mode=1, area=sido["code"], today=today, cmp=cmp)), "sigungu")
        except Exception as e:
            print(f"경고: {sido['name']} 구/군 목록 실패: {e}", file=sys.stderr)

    new, failed = [], 0
    for i, reg in enumerate(regions, 1):
        sy, sm = (prev.year, prev.month) if reg["code"] in have else START
        try:
            series = parse_series(fetch(SERIES_URL.format(code=reg["code"], sy=sy, sm=sm, ey=now.year, em=now.month)))
        except Exception as e:
            series = []
            print(f"경고: {reg['name']}({reg['code']}) 실패: {e}", file=sys.stderr)
        if not series:  # 빈/차단 응답이면 기존 데이터 유지
            failed += 1
            continue
        new += [{**s, **reg} for s in series]
        if i % 50 == 0:
            print(f"{i}/{len(regions)}")

    if not regions:
        sys.exit("지역 목록이 비었습니다. CSV를 건드리지 않습니다.")
    if not new:
        sys.exit("수집된 데이터가 없습니다 (차단 의심). CSV를 건드리지 않습니다.")
    rows = merge(old, new)
    os.makedirs(os.path.dirname(CSV_PATH), exist_ok=True)
    tmp = CSV_PATH + ".tmp"
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    os.replace(tmp, CSV_PATH)
    print(f"지역 {len(regions)}개 (실패 {failed}), 새 행 {len(new)}, 전체 {len(rows)}행")


if __name__ == "__main__":
    main()
