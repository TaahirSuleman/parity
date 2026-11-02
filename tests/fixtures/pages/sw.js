// A worker that phones home as soon as it runs: the fixture server records the /sw-ping request if the worker was ever allowed to make one.
self.addEventListener("install", () => { self.skipWaiting(); fetch(self.location.origin + "/sw-ping?install").catch(() => {}); });
self.addEventListener("activate", () => { fetch(self.location.origin + "/sw-ping?activate").catch(() => {}); });
