from collect import parse_series, parse_regions, parse_region_dates, merge, parse_gin, parse_volume

js = ('chartData[0]={"Date":"23/11/1","VM":6935};'
      'listData[1]={"Date":"23/11/01","VM":6935,"VJ":8040,"VW":6543,"gVM":""};'
      'listData[0]={"Date":"26/11/18","VM":12288,"VJ":4437,"VW":4660};')
assert parse_series(js) == [
    {"date": "2023-11-01", "sale": 6935, "jeonse": 8040, "wolse": 6543},
    {"date": "2026-11-18", "sale": 12288, "jeonse": 4437, "wolse": 4660}]
assert parse_series("chartData.length = 0;") == []
assert parse_series('listData[0]={"Date":"26/11/18","VM":"1,234","VJ":5};') == [
    {"date": "2026-11-18", "sale": 1234, "jeonse": 5, "wolse": 0}]  # 값이 빠져도 지역 전체를 버리지 않음

r = parse_regions('[{"idx":"1","area":"11680","areaname":"서울 강남구","total":"12,288","value":"12,293","rate":"-0.1"}]', "sigungu")
assert r == [{"code": "11680", "name": "서울 강남구", "level": "sigungu"}]

old = [{"date": "2026-11-17", "code": "11", "sale": 1}, {"date": "2026-11-18", "code": "11", "sale": 2}]
new = [{"date": "2026-11-18", "code": "11", "sale": 3}, {"date": "2026-11-19", "code": "11", "sale": 4}]
assert [x["sale"] for x in merge(old, new)] == [1, 3, 4]
assert merge(old, []) == old
html = 'var today = daily ? 20261118 : 0;\n<option value="0">비교날짜</option>\n<option value="20261117">2026년 11월 17일</option><option value="20261116">'
assert parse_region_dates(html) == ("20261118", "20261117")
gin = ('<script>var ssrGin0101Rows = [{"LAWD_CD":"1100000000","LAWD_NM":"서울","TRADE":5371,"yyyymm":"2026-11"},'
       '{"LAWD_CD":"1168000000","LAWD_NM":"강남구","TRADE":9712,"yyyymm":"2026-11"}];\n</script>')
assert parse_gin(gin) == [{"code": "11", "price": 5371, "yyyymm": "2026-11"},
                          {"code": "11680", "price": 9712, "yyyymm": "2026-11"}]
assert parse_gin("<html>no data</html>") == []
vol = ('chartData1.length = 0;\n\tchartData1[0] = {"date":"2024/1","M":225348,"J":84329,"W":188,"M_CNT":199,"J_CNT":1422,"W_CNT":1002};\n'
       '\tchartData1[1] = {"date":"2006/12","M_CNT":695,"J_CNT":0};\n')
assert parse_volume(vol) == [{"month": "2006-12", "sale": 695, "jeonse": 0, "wolse": 0},
                             {"month": "2024-01", "sale": 199, "jeonse": 1422, "wolse": 1002}]
assert parse_volume("chartData1.length = 0;") == []
old = [{"month": "2026-10", "code": "11", "sale": 1}]
assert [x["sale"] for x in merge(old, [{"month": "2026-10", "code": "11", "sale": 2}], key="month")] == [2]
print("ok")
