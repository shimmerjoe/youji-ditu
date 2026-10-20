const CACHE='tay-8f0dbe106e';
const OFFLINE_PAGE='<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>游记地图 · 离线</title><style>body{font-family:system-ui,-apple-system,"Microsoft YaHei",sans-serif;max-width:42rem;margin:12vh auto;padding:0 1.25rem;line-height:1.7;color:#183b3a;background:#f6efe1}h1{font-size:1.6rem}p{color:#4d6765}a,button{min-height:44px;display:inline-flex;align-items:center;padding:0 14px;margin:8px 8px 0 0;border:1px solid #176b5d;border-radius:8px;color:#fff;background:#176b5d;font:inherit;font-weight:700;text-decoration:none}button{color:#176b5d;background:transparent}</style></head><body><main><p>游记地图</p><h1>当前处于离线状态</h1><p>这页还没有缓存。请先联网打开目标城市攻略，之后即可在弱网或离线时继续阅读。</p><p>已访问并缓存的攻略仍可使用；外部核验链接需要恢复网络后打开。</p><a href="__HOME__">返回已缓存首页</a><button type="button" onclick="location.reload()">重新尝试</button></main></body></html>';
const offlineResponse=()=>new Response(OFFLINE_PAGE.replace('__HOME__',new URL('./index.html',self.registration.scope).href),{status:503,headers:{'Content-Type':'text/html;charset=utf-8','Cache-Control':'no-store'}});
const APP_SHELL=["./index.html","./manifest.webmanifest","./assets/travel.css?v=8f0dbe106e","./assets/travel.js?v=8f0dbe106e","./assets/icon-180.png","./assets/icon-192.png","./assets/icon-512.png","./assets/travel-app.js?v=8f0dbe106e","./assets/travel-app.css?v=8f0dbe106e"];
self.addEventListener('install',e=>{e.waitUntil(caches.open(CACHE).then(c=>c.addAll(APP_SHELL)).then(()=>self.skipWaiting()));});
self.addEventListener('activate',e=>{e.waitUntil(Promise.all([
  caches.keys().then(keys=>Promise.all(keys.filter(k=>k.startsWith('tay-')&&k!==CACHE).map(k=>caches.delete(k)))),
  self.clients.claim()
]))});
self.addEventListener('fetch',e=>{
  if(e.request.method!=='GET')return;
  if(e.request.mode==='navigate'||e.request.destination==='document'){
    e.respondWith(caches.open(CACHE).then(async c=>{
      try{const res=await fetch(e.request);if(res&&res.ok)c.put(e.request,res.clone());return res;}
      catch(_){return await c.match(e.request)||offlineResponse();}
    }));return;
  }
  if(e.request.destination==='script'||e.request.destination==='style'){
    e.respondWith(caches.open(CACHE).then(async c=>{
      try{const res=await fetch(e.request);if(res&&res.ok)c.put(e.request,res.clone());return res;}
      catch(_){return await c.match(e.request)||Response.error();}
    }));return;
  }
  e.respondWith(caches.open(CACHE).then(async c=>{
    const hit=await c.match(e.request);
    const net=fetch(e.request).then(res=>{if(res&&res.ok)c.put(e.request,res.clone());return res;}).catch(()=>hit);
    return hit?hit:net;
  }));
});
