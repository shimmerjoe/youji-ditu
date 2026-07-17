(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root) root.RoadtripCore = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

  const PLATEAU_WORDS = ['拉萨', '西藏', '林芝', '日喀则', '青海', '海西', '甘孜', '阿坝', '香格里拉'];
  const MOUNTAIN_WORDS = ['川西', '秦岭', '太行', '天山', '阿勒泰', '张家界', '神农架', '黄山', '长白山'];

  function number(value, fallback) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : fallback;
  }

  function clamp(value, min, max) {
    return Math.min(max, Math.max(min, value));
  }

  function cleanPlace(value) {
    return String(value || '').trim().replace(/(省|市|自治州|自治区|特别行政区)$/u, '');
  }

  function validateInput(input) {
    const errors = [];
    if (!String(input.origin || '').trim()) errors.push('请填写出发地');
    if (!String(input.destination || '').trim()) errors.push('请填写目的地');
    const days = Number(input.days);
    if (!Number.isInteger(days) || days < 1 || days > 30) errors.push('出行天数必须在 1 到 30 天之间');
    return errors;
  }

  function totalDistanceKm(oneWayKm, tripType) {
    const distance = Math.max(0, Math.round(number(oneWayKm, 0)));
    return tripType === 'roundtrip' ? distance * 2 : distance;
  }

  function splitJourney(options) {
    const days = clamp(Math.round(number(options.days, 1)), 1, 30);
    const totalKm = Math.max(0, Math.round(number(options.totalKm, 0)));
    const averageSpeed = clamp(number(options.averageSpeed, 75), 25, 120);
    const base = Math.floor(totalKm / days);
    let remainder = totalKm - base * days;
    return Array.from({ length: days }, (_, index) => {
      const distanceKm = base + (remainder-- > 0 ? 1 : 0);
      return {
        day: index + 1,
        distanceKm,
        driveMinutes: Math.round(distanceKm / averageSpeed * 60),
      };
    });
  }

  function estimateBudget(options) {
    const distance = Math.max(0, number(options.totalKm, 0));
    const days = clamp(Math.round(number(options.days, 1)), 1, 30);
    const travelers = clamp(Math.round(number(options.travelers, 1)), 1, 12);
    const consumption = Math.max(0, number(options.consumption, options.vehicle === 'ev' ? 16 : 8));
    const energyPrice = Math.max(0, number(options.energyPrice, options.vehicle === 'ev' ? 1.4 : 8));
    const energy = Math.round(distance / 100 * consumption * energyPrice);
    const tolls = Math.max(0, Math.round(number(options.tolls, 0)));
    const tickets = Math.max(0, Math.round(number(options.ticketPerPerson, 0) * travelers));
    const lodging = Math.max(0, Math.round(number(options.hotelPerNight, 0) * Math.max(0, days - 1)));
    const meals = Math.max(0, Math.round(number(options.mealPerPersonDay, 0) * travelers * days));
    const subtotal = energy + tolls + tickets + lodging + meals;
    return {
      energy,
      tolls,
      tickets,
      lodging,
      meals,
      low: Math.round(subtotal * 0.9),
      high: Math.round(subtotal * 1.1),
    };
  }

  function buildRiskFlags(input, days) {
    const risks = [];
    const limitMinutes = clamp(number(input.maxDailyHours, 5), 2, 10) * 60;
    const longest = days.reduce((max, day) => Math.max(max, number(day.driveMinutes, 0)), 0);
    if (longest > limitMinutes || longest > 360) {
      risks.push({
        code: 'long-drive',
        title: '单日驾驶偏长',
        detail: `最长一天约 ${Math.round(longest / 60 * 10) / 10} 小时，请至少每 2 小时休息一次，并考虑增加中途住宿。`,
      });
    }
    if (input.vehicle === 'ev') {
      risks.push({
        code: 'charging',
        title: '充电条件需单独复核',
        detail: '长途纯电出行应按实际续航、温度和海拔预留余量，并在导航应用中复核充电站状态。',
      });
    }
    const destination = String(input.destination || '');
    if (PLATEAU_WORDS.some((word) => destination.includes(word))) {
      risks.push({
        code: 'plateau',
        title: '高海拔适应',
        detail: '首日降低活动强度，避免连续赶路；高原天气、道路管制和身体状况应在出发前再次确认。',
      });
    }
    if (MOUNTAIN_WORDS.some((word) => destination.includes(word))) {
      risks.push({
        code: 'mountain-road',
        title: '山区道路',
        detail: '山路驾驶时间通常高于里程估算，雨雪、落石和夜间视线会显著影响通行。',
      });
    }
    risks.push({
      code: 'live-check',
      title: '出发前动态复核',
      detail: '开放时间、门票参考价、预约、限行、施工和天气均可能变化，请以官方当日信息为准。',
    });
    return risks;
  }

  function findCity(value, cities) {
    const needle = cleanPlace(value);
    if (!needle) return null;
    return (cities || []).find((city) => {
      const names = [city.city, city.province, city.title, city.key].map(cleanPlace);
      return names.some((name) => name === needle || name.includes(needle) || needle.includes(name));
    }) || null;
  }

  function inferOfflineOneWayKm(input, cities) {
    if (number(input.estimatedOneWayKm, 0) > 0) return Math.round(number(input.estimatedOneWayKm, 0));
    const origin = findCity(input.origin, cities);
    const destination = findCity(input.destination, cities);
    if (cleanPlace(input.origin) === cleanPlace(input.destination)) return 80;
    if (origin && destination && origin.province === destination.province) return 280;
    const days = clamp(Math.round(number(input.days, 3)), 1, 30);
    return clamp(days * 220, 360, 1800);
  }

  function dayActivities(day, totalDays, destinationData, theme) {
    const highlights = (destinationData && destinationData.highlights) || [];
    const foods = (destinationData && destinationData.foods) || [];
    if (day.day === totalDays) {
      const items = [];
      if (highlights[0]) items.push(`抵达后优先安排：${highlights.slice(0, 2).join('、')}`);
      if (foods[0]) items.push(`晚餐参考：${foods.slice(0, 2).join('、')}`);
      if (!items.length) items.push('抵达后以休息和熟悉住宿片区为主');
      return items;
    }
    if (day.day === 1) return ['检查油量或电量、胎压和证件', '途中每 2 小时安排一次休息'];
    return [`沿途按“${theme || '综合'}”偏好选择一处短停`, '下午尽量在天黑前抵达住宿地'];
  }

  function buildPlan(input, routeData, cities) {
    const errors = validateInput(input);
    if (errors.length) return { errors };
    const destinationData = findCity(input.destination, cities);
    const oneWayKm = routeData && number(routeData.distanceKm, 0) > 0
      ? Math.round(number(routeData.distanceKm, 0))
      : inferOfflineOneWayKm(input, cities);
    const totalKm = totalDistanceKm(oneWayKm, input.tripType || 'oneway');
    const days = splitJourney({ totalKm, days: input.days, averageSpeed: routeData && routeData.averageSpeed || 75 });
    const totalDriveMinutes = routeData && number(routeData.durationMinutes, 0) > 0
      ? Math.round(number(routeData.durationMinutes, 0) * (input.tripType === 'roundtrip' ? 2 : 1))
      : days.reduce((sum, day) => sum + day.driveMinutes, 0);
    const perDayTime = Math.round(totalDriveMinutes / days.length);
    days.forEach((day, index) => {
      day.driveMinutes = index === days.length - 1
        ? totalDriveMinutes - perDayTime * (days.length - 1)
        : perDayTime;
      day.title = index === 0
        ? `${input.origin}出发`
        : index === days.length - 1
          ? (input.tripType === 'roundtrip' ? `返回${input.origin}` : `抵达${input.destination}`)
          : `途中第 ${index + 1} 天`;
      day.activities = dayActivities(day, days.length, destinationData, input.theme);
      if (input.tripType === 'roundtrip' && index === days.length - 1) {
        day.activities = ['返程前确认油量或电量和道路状态', '预留城市入口拥堵与还车整理时间'];
      }
    });
    const ticketPerPerson = number(input.ticketPerPerson, destinationData && destinationData.ticketEstimate || 0);
    const budget = estimateBudget({
      totalKm,
      days: input.days,
      travelers: input.travelers,
      vehicle: input.vehicle,
      consumption: input.consumption,
      energyPrice: input.energyPrice,
      tolls: routeData ? number(routeData.tolls, 0) * (input.tripType === 'roundtrip' ? 2 : 1) : number(input.estimatedTolls, totalKm * 0.28),
      ticketPerPerson,
      hotelPerNight: input.hotelPerNight,
      mealPerPersonDay: input.mealPerPersonDay,
    });
    const plan = {
      id: `roadtrip-${Date.now()}`,
      title: `${input.origin}到${input.destination}自驾路书`,
      generatedAt: input.generatedAt || new Date().toLocaleString('zh-CN', { hour12: false }),
      input: Object.assign({}, input),
      summary: {
        totalKm,
        driveHours: Math.round(totalDriveMinutes / 6) / 10,
        days: Number(input.days),
        oneWayKm,
      },
      days,
      budget,
      risks: buildRiskFlags(input, days),
      destination: destinationData,
      mapMode: routeData ? 'amap' : 'offline',
      sourceNote: routeData
        ? '里程、预计时间和道路收费来自高德地图路线结果；景点、票价与提示来自本站攻略及其标注来源。'
        : '地图密钥尚未配置，当前里程、时间和道路收费为离线估算；出发前请使用导航应用复核。',
    };
    return plan;
  }

  function toMarkdown(plan) {
    const lines = [
      `# ${plan.title}`,
      '',
      `生成时间：${plan.generatedAt}`,
      '',
      `总里程：约 ${plan.summary.totalKm} 公里`,
      `预计驾驶：约 ${plan.summary.driveHours} 小时`,
      `出行天数：${plan.summary.days} 天`,
      `参考预算：¥${plan.budget.low}–¥${plan.budget.high}`,
      '',
      `> ${plan.sourceNote}`,
      '',
      '## 每日安排',
      '',
    ];
    (plan.days || []).forEach((day) => {
      lines.push(`### 第 ${day.day} 天：${day.title}`);
      lines.push('');
      lines.push(`- 驾驶里程：约 ${day.distanceKm} 公里`);
      lines.push(`- 驾驶时间：约 ${Math.round(day.driveMinutes / 6) / 10} 小时`);
      (day.activities || []).forEach((activity) => lines.push(`- ${activity}`));
      lines.push('');
    });
    lines.push('## 预算参考', '');
    lines.push(`- 能源：¥${plan.budget.energy}`);
    lines.push(`- 道路收费：¥${plan.budget.tolls}`);
    lines.push(`- 门票参考：¥${plan.budget.tickets}`);
    lines.push(`- 住宿参考：¥${plan.budget.lodging}`);
    lines.push(`- 餐饮参考：¥${plan.budget.meals}`);
    lines.push('');
    lines.push('## 风险与复核', '');
    (plan.risks || []).forEach((risk) => lines.push(`- **${risk.title}**：${risk.detail}`));
    lines.push('', '本路书仅用于出行决策参考，不提供任何站内交易服务。');
    return lines.join('\n');
  }

  return {
    validateInput,
    totalDistanceKm,
    splitJourney,
    estimateBudget,
    buildRiskFlags,
    inferOfflineOneWayKm,
    buildPlan,
    toMarkdown,
  };
});
