(function () {
  'use strict';

  const core = window.RoadtripCore;
  const cities = window.TRAVEL_ROADTRIP_CITIES || [];
  const config = window.TRAVEL_ROADTRIP_CONFIG || {};
  const $ = (id) => document.getElementById(id);
  const form = $('roadtripForm');
  if (!core || !form) return;

  // Prefer the shared schema-aware adapter. The small fallback keeps this
  // asset usable when opened in isolation or before travel.js has booted.
  const storage = window.TAY_STORAGE || {
    get(key, fallback) {
      try {
        const raw = localStorage.getItem(key);
        return raw == null ? fallback : JSON.parse(raw);
      } catch (_) { return fallback; }
    },
    set(key, value) {
      try { localStorage.setItem(key, JSON.stringify(value)); return true; } catch (_) { return false; }
    },
  };

  const refs = {
    origin: $('rtOrigin'), destination: $('rtDestination'), days: $('rtDays'), startDate: $('rtStartDate'),
    tripType: $('rtTripType'), maxDailyHours: $('rtMaxDailyHours'), routeStrategy: $('rtRouteStrategy'),
    theme: $('rtTheme'), vehicle: $('rtVehicle'), travelers: $('rtTravelers'), consumption: $('rtConsumption'),
    energyPrice: $('rtEnergyPrice'), hotel: $('rtHotel'), meals: $('rtMeals'), tickets: $('rtTickets'),
    estimatedKm: $('rtEstimatedKm'), estimatedTolls: $('rtEstimatedTolls'), error: $('rtError'),
    results: $('rtResults'), status: $('rtMapStatus'), submit: $('rtGenerate'), save: $('rtSave'),
    export: $('rtExport'), share: $('rtShare'), print: $('rtPrint'), saveTip: $('rtSaveTip'), map: $('rtMap'), cityList: $('rtCityList'),
  };
  const mapFrame = document.querySelector('.rt-map-frame');
  const resultActions = document.querySelector('.rt-result-actions');
  const roadtripSteps = Array.from(form.querySelectorAll('[data-rt-step]'));
  const roadtripStepButtons = Array.from(form.querySelectorAll('[data-rt-step-target]'));
  let currentPlan = null;
  let amap = null;
  let driving = null;
  let geocoder = null;

  function setRoadtripStep(step, options) {
    const target = Math.max(1, Math.min(3, Number(step) || 1));
    const shouldFocus = !options || options.focus !== false;
    roadtripSteps.forEach((section) => {
      const active = Number(section.dataset.rtStep) === target;
      section.classList.toggle('is-active', active);
      section.setAttribute('aria-hidden', active ? 'false' : 'true');
    });
    roadtripStepButtons.forEach((button) => {
      if (Number(button.dataset.rtStepTarget) === target) button.setAttribute('aria-current', 'step');
      else button.removeAttribute('aria-current');
    });
    if (shouldFocus) {
      const activeStep = roadtripSteps.find((section) => Number(section.dataset.rtStep) === target);
      const focusTarget = activeStep && activeStep.querySelector('input:not([type="radio"]), select, button');
      if (focusTarget) focusTarget.focus({ preventScroll: true });
    }
  }

  form.classList.add('rt-stepped');
  setRoadtripStep(1, { focus: false });

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
    // 离线模式没有真实路网可画，地图区保持紧凑，让路书结果尽早出现在屏幕上。
    if (mapFrame) mapFrame.classList.toggle('is-idle', plan.mapMode !== 'amap');
    if (resultActions) resultActions.hidden = false;
    refs.save.disabled = refs.export.disabled = refs.print.disabled = false;
    if (refs.share) refs.share.disabled = false;
    const destination = plan.destination || {};
    const rough = plan.distanceBasis === 'heuristic';
    const kmLabel = rough ? '总里程（粗估）' : '总里程';
    const hoursLabel = rough ? '预计驾驶（粗估）' : '预计驾驶';
    const estimateWarning = rough
      ? `<div class="rt-estimate-warning" role="note"><strong>里程是粗估，不是道路里程</strong><p>没有地图服务时，系统只按同城、同省或跨省和出行天数推算单程公里数，能源和道路收费也随之估算。用导航应用查到单程公里数后填进来，结果会准确得多。</p><button type="button" class="rt-action" data-rt-fill-km>填写实际里程</button></div>`
      : '';
    const dayHtml = plan.days.map((day) => `
      <article class="rt-day">
        <span class="rt-day-index">D${day.day}</span>
        <div><h4>${esc(day.title)}</h4><ul>${(day.activities || []).map((item) => `<li>${esc(item)}</li>`).join('')}</ul></div>
        <div class="rt-day-meta"><strong>${rough ? '约 ' : ''}${day.distanceKm} 公里</strong><span>${esc(formatHours(day.driveMinutes))}</span></div>
      </article>`).join('');
    const riskHtml = plan.risks.map((risk) => `<div class="rt-risk"><strong>${esc(risk.title)}</strong><p>${esc(risk.detail)}</p></div>`).join('');
    const sources = (destination.sources || []).slice(0, 6);
    const sourceLinks = sources.map((url) => `<a href="${esc(url)}" target="_blank" rel="noreferrer">${esc(domain(url))}</a>`).join('');
    refs.results.innerHTML = `
      <div class="rt-result-head"><p class="eyebrow">Roadbook</p><h2>${esc(plan.title)}</h2><p>${esc(plan.sourceNote)}</p></div>
      ${estimateWarning}
      <div class="rt-summary-grid">
        <div class="rt-metric${rough ? ' is-rough' : ''}"><span>${kmLabel}</span><strong>${rough ? '约 ' : ''}${plan.summary.totalKm} 公里</strong></div>
        <div class="rt-metric${rough ? ' is-rough' : ''}"><span>${hoursLabel}</span><strong>${rough ? '约 ' : ''}${plan.summary.driveHours} 小时</strong></div>
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
        setMapStatus(plan.distanceBasis === 'user' ? '离线模式：地图服务未配置，里程按你填写的公里数计算。' : '离线模式：地图服务未配置，里程为粗估，请见下方说明。');
      }
    } catch (error) {
      plan = core.buildPlan(input, null, cities);
      setMapStatus(`地图计算未完成，已回退离线估算：${error.message}`);
    } finally {
      setBusy(false);
    }
    renderPlan(plan);
    storage.set('tay_last_roadtrip', plan);
    refs.results.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  function savePlan() {
    if (!currentPlan) return;
    let saved = storage.get('tay_roadtrips', []);
    if (!Array.isArray(saved)) saved = [];
    saved = saved.filter((plan) => plan.id !== currentPlan.id);
    saved.unshift(currentPlan);
    storage.set('tay_roadtrips', saved.slice(0, 20));
    refs.saveTip.hidden = false;
    setTimeout(() => { refs.saveTip.hidden = true; }, 1800);
  }

  function encodeSharePlan(plan) {
    const bytes = new TextEncoder().encode(JSON.stringify(plan));
    let binary = '';
    bytes.forEach((byte) => { binary += String.fromCharCode(byte); });
    return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/g, '');
  }

  function decodeSharePlan(token) {
    if (!token || token.length > 16000) return null;
    try {
      const padded = token.replace(/-/g, '+').replace(/_/g, '/') + '='.repeat((4 - (token.length % 4)) % 4);
      const binary = atob(padded);
      const bytes = Uint8Array.from(binary, (char) => char.charCodeAt(0));
      const plan = JSON.parse(new TextDecoder().decode(bytes));
      if (!plan || typeof plan !== 'object' || !plan.input || !Array.isArray(plan.days) || !plan.summary) return null;
      return plan;
    } catch (_) { return null; }
  }

  async function sharePlan() {
    if (!currentPlan) return;
    const url = new URL(location.href);
    url.searchParams.delete('plan');
    url.hash = `plan=${encodeSharePlan(currentPlan)}`;
    history.replaceState(null, '', url);
    const shareUrl = url.toString();
    setMapStatus('已生成便携分享链接；链接包含本次路书数据，不会上传到服务器。');
    try {
      if (navigator.share) {
        await navigator.share({ title: currentPlan.title, text: '游记地图自驾路书', url: shareUrl });
      } else if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(shareUrl);
        setMapStatus('分享链接已复制到剪贴板；接收方打开后可直接恢复路书。');
      }
    } catch (_) {
      // Browser share dialogs can be dismissed; the URL remains in the address bar.
    }
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
    const sharedToken = new URLSearchParams(location.hash.replace(/^#/, '')).get('plan');
    const sharedPlan = decodeSharePlan(sharedToken);
    if (sharedPlan) {
      fillForm(sharedPlan.input);
      renderPlan(sharedPlan);
      setMapStatus('已从分享链接恢复路书；这是链接内的快照，重新生成可刷新路线数据。');
      return;
    }
    const id = new URLSearchParams(location.search).get('plan');
    let saved = storage.get('tay_roadtrips', []);
    if (!Array.isArray(saved)) saved = [];
    const plan = id ? saved.find((item) => item.id === id) : null;
    if (plan) { fillForm(plan.input); renderPlan(plan); setMapStatus('已打开本机保存的路书；重新生成可刷新路线数据。'); return; }
    const last = storage.get('tay_last_roadtrip', null);
    if (last && last.input) {
      fillForm(last.input);
      renderPlan(last);
      setMapStatus('已恢复上次生成的路书；重新生成可刷新路线数据。');
    }
  }

  if (refs.cityList) {
    const names = [...new Set(cities.map((city) => city.city).filter(Boolean))];
    refs.cityList.innerHTML = names.map((name) => `<option value="${esc(name)}"></option>`).join('');
  }
  if (!refs.startDate.value) refs.startDate.value = new Date().toISOString().slice(0, 10);
  roadtripStepButtons.forEach((button) => button.addEventListener('click', () => setRoadtripStep(button.dataset.rtStepTarget)));
  form.querySelectorAll('[data-rt-next]').forEach((button) => button.addEventListener('click', () => setRoadtripStep(button.dataset.rtNext)));
  form.querySelectorAll('[data-rt-back]').forEach((button) => button.addEventListener('click', () => setRoadtripStep(button.dataset.rtBack)));
  refs.vehicle.addEventListener('change', () => updateVehicleDefaults(true));
  form.addEventListener('submit', (event) => { event.preventDefault(); generate(); });
  refs.save.addEventListener('click', savePlan);
  if (refs.share) refs.share.addEventListener('click', sharePlan);
  refs.export.addEventListener('click', exportPlan);
  refs.print.addEventListener('click', () => window.print());
  refs.results.addEventListener('click', (event) => {
    if (!event.target.closest('[data-rt-fill-km]')) return;
    setRoadtripStep('3');
    const details = refs.estimatedKm.closest('details');
    if (details) details.open = true;
    refs.estimatedKm.scrollIntoView({ block: 'center', behavior: 'smooth' });
    refs.estimatedKm.focus({ preventScroll: true });
  });
  updateVehicleDefaults(false);
  restoreSavedPlan();
  if (config.amapJsKey) setMapStatus('地图服务已配置，生成路书时将计算真实路网。');
})();
