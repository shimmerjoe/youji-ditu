const test = require('node:test');
const assert = require('node:assert/strict');

const core = require('./roadtrip-core.js');

test('rejects an incomplete road trip request', () => {
  const errors = core.validateInput({ origin: '', destination: '成都', days: 0 });
  assert.deepEqual(errors, ['请填写出发地', '出行天数必须在 1 到 30 天之间']);
});

test('calculates round trip distance without changing one-way plans', () => {
  assert.equal(core.totalDistanceKm(620, 'oneway'), 620);
  assert.equal(core.totalDistanceKm(620, 'roundtrip'), 1240);
  assert.equal(core.totalDistanceKm(620, 'loop'), 620);
});

test('splits all mileage across the requested number of days', () => {
  const days = core.splitJourney({ totalKm: 960, days: 4, averageSpeed: 80 });
  assert.equal(days.length, 4);
  assert.equal(days.reduce((sum, day) => sum + day.distanceKm, 0), 960);
  assert.deepEqual(days.map((day) => day.distanceKm), [240, 240, 240, 240]);
  assert.ok(days.every((day) => day.driveMinutes === 180));
});

test('estimates fuel, ticket, lodging and meal budgets as a range', () => {
  const budget = core.estimateBudget({
    totalKm: 1000,
    days: 5,
    travelers: 2,
    vehicle: 'gas',
    consumption: 8,
    energyPrice: 8,
    tolls: 260,
    ticketPerPerson: 300,
    hotelPerNight: 320,
    mealPerPersonDay: 120,
  });
  assert.equal(budget.energy, 640);
  assert.equal(budget.tolls, 260);
  assert.equal(budget.tickets, 600);
  assert.equal(budget.lodging, 1280);
  assert.equal(budget.meals, 1200);
  assert.equal(budget.low, 3582);
  assert.equal(budget.high, 4378);
});

test('uses electricity consumption for electric vehicles', () => {
  const budget = core.estimateBudget({
    totalKm: 600,
    days: 3,
    travelers: 1,
    vehicle: 'ev',
    consumption: 16,
    energyPrice: 1.4,
    tolls: 100,
    ticketPerPerson: 0,
    hotelPerNight: 0,
    mealPerPersonDay: 0,
  });
  assert.equal(budget.energy, 134);
});

test('flags unsafe daily driving and electric charging checks', () => {
  const risks = core.buildRiskFlags(
    { vehicle: 'ev', maxDailyHours: 4, destination: '拉萨' },
    [{ driveMinutes: 420 }, { driveMinutes: 180 }],
  );
  assert.ok(risks.some((item) => item.code === 'long-drive'));
  assert.ok(risks.some((item) => item.code === 'charging'));
  assert.ok(risks.some((item) => item.code === 'plateau'));
});

test('exports a non-transactional markdown roadbook', () => {
  const markdown = core.toMarkdown({
    title: '郑州到成都自驾路书',
    generatedAt: '2026-07-11 15:00',
    sourceNote: '地图数据未接入，当前为离线估算。',
    summary: { totalKm: 1200, driveHours: 15, days: 4 },
    days: [{ day: 1, title: '郑州到西安', distanceKm: 480, driveMinutes: 360, activities: ['下午抵达后休息'] }],
    budget: { low: 3000, high: 3900 },
    risks: [{ title: '长距离驾驶', detail: '建议每两小时休息。' }],
  });
  assert.match(markdown, /# 郑州到成都自驾路书/);
  assert.match(markdown, /参考预算：¥3000–¥3900/);
  assert.match(markdown, /地图数据未接入/);
  assert.doesNotMatch(markdown, /立即购买|下单|支付/);
});

test('round trips finish back at the origin', () => {
  const plan = core.buildPlan({
    origin: '郑州', destination: '成都', days: 4, tripType: 'roundtrip',
    travelers: 2, vehicle: 'gas', consumption: 8, energyPrice: 8,
    hotelPerNight: 300, mealPerPersonDay: 100, maxDailyHours: 6,
  }, { distanceKm: 600, durationMinutes: 480, tolls: 280 }, []);
  assert.equal(plan.summary.totalKm, 1200);
  assert.match(plan.days.at(-1).title, /返回郑州/);
});
