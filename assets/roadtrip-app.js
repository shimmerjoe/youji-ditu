(function () {
  'use strict';

  const core = window.RoadtripCore;
  const cities = window.TRAVEL_ROADTRIP_CITIES || [];
  const config = window.TRAVEL_ROADTRIP_CONFIG || {};
  const $ = (id) => document.getElementById(id);
  const form = $('roadtripForm');
  if (!core || !form) return;

  const refs = {
    origin: $('rtOrigin'), destination: $('rtDestination'), days: $('rtDays'), startDate: $('rtStartDate'),
    tripType: $('rtTripType'), maxDailyHours: $('rtMaxDailyHours'), routeStrategy: $('rtRouteStrategy'),
    theme: $('rtTheme'), vehicle: $('rtVehicle'), travelers: $('rtTravelers'), consumption: $('rtConsumption'),
    energyPrice: $('rtEnergyPrice'), hotel: $('rtHotel'), meals: $('rtMeals'), tickets: $('rtTickets'),
    estimatedKm: $('rtEstimatedKm'), estimatedTolls: $('rtEstimatedTolls'), error: $('rtError'),
    results: $('rtResults'), status: $('rtMapStatus'), submit: $('rtGenerate'), save: $('rtSave'),
    export: $('rtExport'), print: $('rtPrint'), saveTip: $('rtSaveTip'), map: $('rtMap'), cityList: $('rtCityList'),
  };
  let currentPlan = null;
  let amap = null;
  let driving = null;
  let geocoder = null;

  function esc(value) {
    return String(value == null ? '' : value).replace(/[&<>"']/g, (char) => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
    }[char]));
  }

  function domain(url) {
    try { return new URL(url).hostname.replace(/^www\./, ''); } catch (_) { return '资料来源'; }
  }

  function getTripType() {
    const checked = form.querySelector('input[name="rtTripType"]:checked');
    return checked ? checked.value : 'oneway';
  }

  function collectInput() {
    return {
      origin: refs.origin.value.trim(),
      destination: refs.destination.value.trim(),
      days: Number(refs.days.value),
      startDate: refs.startDate.value,
      tripType: getTripType(),
      maxDailyHours: Number(refs.maxDailyHours.value),
      routeStrategy: refs.routeStrategy.value,
      theme: refs.theme.value,
      vehicle: refs.vehicle.value,
      travelers: Number(refs.travelers.value),
      consumption: Number(refs.consumption.value),
      energyPrice: Number(refs.energyPrice.value),
      hotelPerNight: Number(refs.hotel.value),
      mealPerPersonDay: Number(refs.meals.value),
      ticketPerPerson: Number(refs.tickets.value),
      estimatedOneWayKm: Number(refs.estimatedKm.value),
      estimatedTolls: Number(refs.estimatedTolls.value),
    };
  }

  function fillForm(input) {
    if (!input) return;
    const mapping = {
      origin: refs.origin, destination: refs.destination, days: refs.days, startDate: refs.startDate,
      maxDailyHours: refs.maxDailyHours, routeStrategy: refs.routeStrategy, theme: refs.theme,
      vehicle: refs.vehicle, travelers: refs.travelers, consumption: refs.consumption,
      energyPrice: refs.energyPrice, hotelPerNight: refs.hotel, mealPerPersonDay: refs.meals,
      ticketPerPerson: refs.tickets, estimatedOneWayKm: refs.estimatedKm, estimatedTolls: refs.estimatedTolls,
    };
    Object.keys(mapping).forEach((key) => { if (input[key] != null) mapping[key].value = input[key]; });
    const tripType = form.querySelector(`input[name="rtTripType"][value="${input.tripType || 'oneway'}"]`);
    if (tripType) tripType.checked = true;
    updateVehicleDefaults(false);
  }

  function setError(messages) {
    refs.error.textContent = Array.isArray(messages) ? messages.join('；') : String(messages || '');
  }

  function setBusy(busy) {
    refs.submit.disabled = busy;
    refs.submit.textContent = busy ? '正在计算路线…' : '生成自驾路书';
  }

  function setMapStatus(message) { refs.status.textContent = message; }

  function updateVehicleDefaults(replaceValues) {
    const ev = refs.vehicle.value === 'ev';
    const phev = refs.vehicle.value === 'phev';
    const labelConsumption = document.querySelector('[data-label="consumption"]');
    const labelEnergy = document.querySelector('[data-label="energy-price"]');
    if (labelConsumption) labelConsumption.textContent = ev ? '百公里电耗' : '百公里油耗';
    if (labelEnergy) labelEnergy.textContent = ev ? '充电单价' : '燃油单价';
    if (replaceValues) {
      refs.consumption.value = ev ? '16' : (phev ? '5.5' : '8');
      refs.energyPrice.value = ev ? '1.4' : '8';
    }
  }

  function formatHours(minutes) { return `${Math.round(Number(minutes || 0) / 6) / 10} 小时`; }
  function currency(value) { return `¥${Math.round(Number(value || 0)).toLocaleString('zh-CN')}`; }

  function renderPlan(plan) {
    currentPlan = plan;
    refs.save.disabled = refs.export.disabled = refs.print.disabled = false;
    const destination = plan.destination || {};
    const dayHtml = plan.days.map((day) => `
      <article class="rt-day">
        <span class="rt-day-index">D${day.day}</span>
        <div><h4>${esc(day.title)}</h4><ul>${(day.activities || []).map((item) => `<li>${esc(item)}</li>`).join('')}</ul></div>
        <div class="rt-day-meta"><strong>${day.distanceKm} 公里</strong><span>${esc(formatHours(day.driveMinutes))}</span></div>
      </article>`).join('');
    const riskHtml = plan.risks.map((risk) => `<div class="rt-risk"><strong>${esc(risk.title)}</strong><p>${esc(risk.detail)}</p></div>`).join('');
    const sources = (destination.sources || []).slice(0, 6);
    const sourceLinks = sources.map((url) => `<a href="${esc(url)}" target="_blank" rel="noreferrer">${esc(domain(url))}</a>`).join('');
    refs.results.innerHTML = `
      <div class="rt-result-head"><p class="eyebrow">Roadbook</p><h2>${esc(plan.title)}</h2><p>${esc(plan.sourceNote)}</p></div>
      <div class="rt-summary-grid">
        <div class="rt-metric"><span>总里程</span><strong>${plan.summary.totalKm} 公里</strong></div>
        <div class="rt-metric"><span>预计驾驶</span><strong>${plan.summary.driveHours} 小时</strong></div>
        <div class="rt-metric"><span>行程天数</span><strong>${plan.summary.days} 天</strong></div>
        <div class="rt-metric"><span>参考预算</span><strong>${currency(plan.budget.low)}–${currency(plan.budget.high).replace('¥', '')}</strong></div>
      </div>
      <section class="rt-section"><h3>逐日安排</h3><div class="rt-days">${dayHtml}</div></section>
      <section class="rt-section"><h3>预算拆分</h3><div class="rt-budget">
        <div><span>能源</span><strong>${currency(plan.budget.energy)}</strong></div>
        <div><span>道路收费</span><strong>${currency(plan.budget.tolls)}</strong></div>
        <div><span>门票参考</span><strong>${currency(plan.budget.tickets)}</strong></div>
        <div><span>住宿参考</span><strong>${currency(plan.budget.lodging)}</strong></div>
        <div><span>餐饮参考</span><strong>${currency(plan.budget.meals)}</strong></div>
      </div><p class="rt-price-note">价格仅用于预算估算，不提供站内交易。门票、住宿、能源和道路收费会随日期、车型及政策变化。</p></section>
      <section class="rt-section"><h3>风险与复核</h3><div class="rt-risk-list">${riskHtml}</div></section>
      <section class="rt-section"><h3>资料来源</h3><p class="rt-source-note">城市攻略更新时间：${esc(destination.updatedAt || '未标注')}。链接仅用于核验信息，不是购买入口。</p><div class="rt-source-links">${sourceLinks || '<span class="rt-field-note">当前城市攻略尚未收录外部来源，请优先核对当地文旅与景区官网。</span>'}</div></section>`;
  }

  function loadAmap() {
    if (!config.amapJsKey) return Promise.resolve(false);
    if (window.AMap) return Promise.resolve(true);
    if (config.amapSecurityCode) window._AMapSecurityConfig = { securityJsCode: config.amapSecurityCode };
    return new Promise((resolve, reject) => {
      const script = document.createElement('script');
      script.src = `https://webapi.amap.com/maps?v=2.0&key=${encodeURIComponent(config.amapJsKey)}&plugin=AMap.Driving,AMap.Geocoder,AMap.AutoComplete`;
      script.async = true;
      script.onload = () => resolve(true);
      script.onerror = () => reject(new Error('高德地图资源加载失败'));
      document.head.appendChild(script);
    });
  }

  function drivingPolicy(strategy) {
    if (!window.AMap) return 0;
    const policies = window.AMap.DrivingPolicy || {};
    return {
      standard: policies.LEAST_TIME || 0,
      fast: policies.REAL_TRAFFIC || policies.LEAST_TIME || 0,
      toll: policies.LEAST_FEE || 1,
      nohighway: 3,
    }[strategy] || policies.LEAST_TIME || 0;
  }

  function calculateAmap(input) {
    return new Promise((resolve, reject) => {
      if (!amap) amap = new AMap.Map('rtMap', { zoom: 6, resizeEnable: true, viewMode: '2D' });
      if (driving) driving.clear();
      driving = new AMap.Driving({ map: amap, policy: drivingPolicy(input.routeStrategy), hideMarkers: false, showTraffic: false });
      driving.search(
        [{ keyword: input.origin, city: '全国' }],
        [{ keyword: input.destination, city: '全国' }],
        (status, result) => {
          if (status !== 'complete' || !result || !result.routes || !result.routes.length) {
            reject(new Error(result && result.info || '未找到可用驾车路线'));
            return;
          }
          const route = result.routes[0];
          const distanceKm = Math.max(1, Math.round(Number(route.distance || 0) / 1000));
          const durationMinutes = Math.max(1, Math.round(Number(route.time || 0) / 60));
          resolve({
            metrics: {
              distanceKm,
              durationMinutes,
              tolls: Math.round(Number(route.tolls || 0)),
              averageSpeed: Math.max(35, Math.min(100, Math.round(distanceKm / (durationMinutes / 60)))),
            },
            route,
          });
        },
      );
    });
  }

  function routePoints(route) {
    const points = [];
    (route.steps || []).forEach((step) => (step.path || []).forEach((point) => points.push(point)));
    return points;
  }

  function reverseGeocode(point) {
    if (!geocoder) geocoder = new AMap.Geocoder({ radius: 1000 });
    return new Promise((resolve) => {
      geocoder.getAddress(point, (status, result) => {
        if (status !== 'complete' || !result.regeocode) return resolve('沿途城市');
        const component = result.regeocode.addressComponent || {};
        const city = Array.isArray(component.city) ? '' : component.city;
        resolve(city || component.district || component.province || '沿途城市');
      });
    });
  }

  async function enrichDailyStops(plan, route) {
    const points = routePoints(route);
    if (points.length < 3 || plan.days.length < 2) return plan;
    for (let index = 0; index < plan.days.length - 1; index += 1) {
      const pointIndex = Math.min(points.length - 1, Math.round(points.length * (index + 1) / plan.days.length));
      const stop = await reverseGeocode(points[pointIndex]);
      plan.days[index].title = index === 0 ? `${plan.input.origin}到${stop}` : `前往${stop}`;
      plan.days[index].activities.push(`建议住宿或休息片区：${stop}`);
    }
    plan.days[plan.days.length - 1].title = plan.input.tripType === 'roundtrip'
      ? `返回${plan.input.origin}`
      : `抵达${plan.input.destination}`;
    return plan;
  }

  async function generate() {
    setError('');
    const input = collectInput();
    const errors = core.validateInput(input);
    if (errors.length) { setError(errors); return; }
    setBusy(true);
    let plan;
    try {
      const hasMap = await loadAmap();
      if (hasMap) {
        setMapStatus('正在使用高德地图计算真实路网…');
        const routeResult = await calculateAmap(input);
        plan = core.buildPlan(input, routeResult.metrics, cities);
        plan = await enrichDailyStops(plan, routeResult.route);
        setMapStatus('已使用高德地图路网；出发前仍需复核实时管制和天气。');
      } else {
        plan = core.buildPlan(input, null, cities);
        setMapStatus('离线估算模式：填写高德 JS Key 后可显示真实地图、里程、时间和道路收费。');
      }
    } catch (error) {
      plan = core.buildPlan(input, null, cities);
      setMapStatus(`地图计算未完成，已回退离线估算：${error.message}`);
    } finally {
      setBusy(false);
    }
    renderPlan(plan);
    try { localStorage.setItem('tay_last_roadtrip', JSON.stringify(plan)); } catch (_) {}
    refs.results.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  function savePlan() {
    if (!currentPlan) return;
    let saved = [];
    try { saved = JSON.parse(localStorage.getItem('tay_roadtrips') || '[]'); } catch (_) {}
    saved = saved.filter((plan) => plan.id !== currentPlan.id);
    saved.unshift(currentPlan);
    try { localStorage.setItem('tay_roadtrips', JSON.stringify(saved.slice(0, 20))); } catch (_) {}
    refs.saveTip.hidden = false;
    setTimeout(() => { refs.saveTip.hidden = true; }, 1800);
  }

  function exportPlan() {
    if (!currentPlan) return;
    const blob = new Blob(['\ufeff' + core.toMarkdown(currentPlan)], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${currentPlan.title}.md`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  }

  function restoreSavedPlan() {
    const id = new URLSearchParams(location.search).get('plan');
    let saved = [];
    try { saved = JSON.parse(localStorage.getItem('tay_roadtrips') || '[]'); } catch (_) {}
    const plan = id ? saved.find((item) => item.id === id) : null;
    if (plan) { fillForm(plan.input); renderPlan(plan); setMapStatus('已打开本机保存的路书；重新生成可刷新路线数据。'); return; }
    let last = null;
    try { last = JSON.parse(localStorage.getItem('tay_last_roadtrip') || 'null'); } catch (_) {}
    if (last && last.input) fillForm(last.input);
  }

  if (refs.cityList) {
    const names = [...new Set(cities.map((city) => city.city).filter(Boolean))];
    refs.cityList.innerHTML = names.map((name) => `<option value="${esc(name)}"></option>`).join('');
  }
  if (!refs.startDate.value) refs.startDate.value = new Date().toISOString().slice(0, 10);
  refs.vehicle.addEventListener('change', () => updateVehicleDefaults(true));
  form.addEventListener('submit', (event) => { event.preventDefault(); generate(); });
  refs.save.addEventListener('click', savePlan);
  refs.export.addEventListener('click', exportPlan);
  refs.print.addEventListener('click', () => window.print());
  updateVehicleDefaults(false);
  restoreSavedPlan();
  if (config.amapJsKey) setMapStatus('地图服务已配置，生成路书时将计算真实路网。');
})();
