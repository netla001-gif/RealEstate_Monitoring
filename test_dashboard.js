// index.html 의 계산 함수 검사: node test_dashboard.js
const html = require("fs").readFileSync(__dirname + "/index.html", "utf8");
const src = html.match(/\/\/ <pure>([\s\S]*?)\/\/ <\/pure>/)[1];
const { rate, shortName, volRate, settled } = new Function("latest", src + "; return { rate, shortName, volRate, settled };")("2026-11-18");
const assert = require("assert");

const r = { dates: ["2026-11-10", "2026-11-18"], sale: [100, 110], jeonse: [0, 5] };
assert(Math.abs(rate(r, "sale", 7) - 10) < 1e-9);              // 11-11 없음 → 직전 11-10 사용
assert.strictEqual(rate(r, "jeonse", 7), null);                // 기준값 0 → null
assert.strictEqual(rate(r, "sale", 30), null);                 // 비교할 이전 날짜 없음 → null
assert.strictEqual(rate({ ...r, dates: ["2026-11-10", "2026-11-17"] }, "sale", 7), null); // 최신일 누락 지역 → null
assert.strictEqual(shortName({ level: "sigungu", name: "서울 강남구" }), "강남구");
assert.strictEqual(shortName({ level: "sido", name: '<b x="1">&' }), "&lt;b x=&quot;1&quot;&gt;&amp;");
const months = Array.from({ length: 14 }, (_, i) => `2025-${String(i + 1).padStart(2, "0")}`);
const v = { months, sale: [...Array(12).fill(100), 150, 5], jeonse: [...Array(12).fill(0), 3, 1] };
assert.strictEqual(volRate(v, "sale", months[12]), 50);         // 150 / 평균 100 → +50%
assert.strictEqual(volRate(v, "jeonse", months[12]), null);     // 평균 0 → null
assert.strictEqual(volRate(v, "sale", months[11]), null);       // 직전 12개월이 모자람 → null
assert.strictEqual(volRate(undefined, "sale", months[12]), null); // 거래량 데이터 없는 지역
assert.strictEqual(settled("2026-09", "2026-11-18"), true);   // 9/30 + 30일 = 10/30 < 11/18
assert.strictEqual(settled("2026-10", "2026-11-18"), false);  // 10/31 + 30일 = 11/30 → 아직 집계 중
assert.strictEqual(settled("2026-10", "2026-12-01"), true);
console.log("ok");
