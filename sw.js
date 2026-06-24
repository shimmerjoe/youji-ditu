const CACHE='tay-v1';
self.addEventListener('install',e=>{self.skipWaiting();});
self.addEventListener('activate',e=>{e.waitUntil(self.clients.claim());});
self.addEventListener('fetch',e=>{
  if(e.request.method!=='GET')return;
  e.respondWith(caches.open(CACHE).then(c=>c.match(e.request).then(hit=>{
    const net=fetch(e.request).then(res=>{try{c.put(e.request,res.clone());}catch(_){}
      return res;}).catch(()=>hit);
    return hit||net;
  })));
});
