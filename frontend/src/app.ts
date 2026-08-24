import "./app.css";
import {
  connectionStatus,
  shouldAnnounceWorkerUpdate,
  workerUpdateStatus,
  type ConnectionStatus,
} from "./connection-status";
import { bootstrapSiteSearch } from "./site-search";

function bootstrapRuntime(): void {
  const node = document.createElement("div");
  node.id = "appRuntimeStatus";
  node.className = "app-runtime-status";
  node.setAttribute("role", "status");
  node.setAttribute("aria-live", "polite");
  node.hidden = true;
  document.body.append(node);

  let hideTimer: number | undefined;
  const show = (status: ConnectionStatus): void => {
    if (hideTimer !== undefined) window.clearTimeout(hideTimer);
    node.dataset.kind = status.kind;
    node.textContent = status.message;
    node.hidden = false;
    if (!status.persistent) {
      hideTimer = window.setTimeout(() => {
        node.hidden = true;
      }, 2400);
    }
  };

  window.addEventListener("offline", () => show(connectionStatus(false)));
  window.addEventListener("online", () => show(connectionStatus(true)));
  const serviceWorker = navigator.serviceWorker;
  let previouslyControlled = Boolean(serviceWorker?.controller);
  serviceWorker?.addEventListener("controllerchange", () => {
    if (shouldAnnounceWorkerUpdate(previouslyControlled)) show(workerUpdateStatus());
    previouslyControlled = true;
  });

  document.documentElement.dataset.appRuntime = "ready";
  if (!navigator.onLine) show(connectionStatus(false));
  bootstrapSiteSearch();
}

if (typeof document !== "undefined") {
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bootstrapRuntime, { once: true });
  } else {
    bootstrapRuntime();
  }
}
