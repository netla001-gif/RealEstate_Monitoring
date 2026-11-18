// index.html 의 계산 함수 검사: node test_dashboard.js
const html = require("fs").readFileSync(__dirname + "/index.html", "utf8");
const src = html.match(/\/\/ <pure>([\s\S]*?)\/\/ <\/pure>/)[1];
const { rate, shortName } = new Function("latest", src + "; return { rate, shortName };")("2026-11-18");
const assert = require("assert");

const r = { dates: ["2026-11-10", "2026-11-18"], sale: [100, 110], jeonse: [0, 5] };
assert(Math.abs(rate(r, "sale", 7) - 10) < 1e-9);              // 11-11 없음 → 직전 11-10 사용
assert.strictEqual(rate(r, "jeonse", 7), null);                // 기준값 0 → null
assert.strictEqual(rate(r, "sale", 30), null);                 // 비교할 이전 날짜 없음 → null
assert.strictEqual(rate({ ...r, dates: ["2026-11-10", "2026-11-17"] }, "sale", 7), null); // 최신일 누락 지역 → null
assert.strictEqual(shortName({ level: "sigungu", name: "서울 강남구" }), "강남구");
assert.strictEqual(shortName({ level: "sido", name: '<b x="1">&' }), "&lt;b x=&quot;1&quot;&gt;&amp;");
console.log("ok");
