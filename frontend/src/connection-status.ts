export type ConnectionKind = "online" | "offline";

export interface ConnectionStatus {
  kind: ConnectionKind;
  message: string;
  persistent: boolean;
}

export function connectionStatus(online: boolean): ConnectionStatus {
  return online
    ? { kind: "online", message: "网络已恢复，最新资料可继续加载。", persistent: false }
    : { kind: "offline", message: "当前离线：已访问的攻略仍可阅读，外部核验链接暂不可用。", persistent: true };
}

export function shouldAnnounceWorkerUpdate(previouslyControlled: boolean): boolean {
  return previouslyControlled;
}

export function workerUpdateStatus(): ConnectionStatus {
  return {
    kind: "online",
    message: "旅行应用已更新到最新版本。",
    persistent: false,
  };
}
