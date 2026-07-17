const CACHE='tay-9b552e20a2';
const APP_SHELL=["./index.html","./manifest.webmanifest","./assets/travel.css?v=9b552e20a2","./assets/travel.js?v=9b552e20a2","./assets/search-index.js?v=9b552e20a2","./assets/icon-180.png","./assets/icon-192.png","./assets/icon-512.png"];
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
      catch(_){return await c.match(e.request)||Response.error();}
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
