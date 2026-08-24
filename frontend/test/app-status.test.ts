import assert from "node:assert/strict";
import test from "node:test";
import {
  connectionStatus,
  shouldAnnounceWorkerUpdate,
  workerUpdateStatus,
} from "../src/connection-status.ts";

test("offline state explains the capability boundary and stays visible", () => {
  const status = connectionStatus(false);
  assert.equal(status.kind, "offline");
  assert.equal(status.persistent, true);
  assert.match(status.message, /离线/);
  assert.match(status.message, /外部核验链接/);
});

test("online recovery is concise and temporary", () => {
  const status = connectionStatus(true);
  assert.equal(status.kind, "online");
  assert.equal(status.persistent, false);
  assert.match(status.message, /网络已恢复/);
});

test("service worker only announces a real controller replacement", () => {
  assert.equal(shouldAnnounceWorkerUpdate(false), false);
  assert.equal(shouldAnnounceWorkerUpdate(true), true);
  assert.match(workerUpdateStatus().message, /更新/);
  assert.equal(workerUpdateStatus().persistent, false);
});
