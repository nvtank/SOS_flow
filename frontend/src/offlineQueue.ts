import { api } from "./api/client";

export type SyncStatus = "QUEUED" | "SYNCING" | "SYNCED" | "FAILED";
export type OfflineReport = {
  local_id: string;
  client_submission_id: string;
  form_data: Record<string, unknown>;
  created_at_local: string;
  sync_status: SyncStatus;
  retry_count: number;
  last_error?: string;
  next_retry_at?: string;
};

const DB_NAME = "sosflow-offline";
const STORE = "reports";

function openDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, 1);
    request.onerror = () => reject(request.error);
    request.onupgradeneeded = () => request.result.createObjectStore(STORE, { keyPath: "local_id" });
    request.onsuccess = () => resolve(request.result);
  });
}

async function transact<T>(mode: IDBTransactionMode, action: (store: IDBObjectStore) => IDBRequest<T>): Promise<T> {
  const db = await openDb();
  return new Promise<T>((resolve, reject) => {
    const request = action(db.transaction(STORE, mode).objectStore(STORE));
    request.onsuccess = () => resolve(request.result as T);
    request.onerror = () => reject(request.error);
  }).finally(() => db.close());
}

export function makeOfflineReport(formData: Record<string, unknown>): OfflineReport {
  const id = crypto.randomUUID();
  return { local_id: `LOCAL-${id.slice(0, 8).toUpperCase()}`, client_submission_id: id, form_data: formData, created_at_local: new Date().toISOString(), sync_status: "QUEUED", retry_count: 0 };
}

export const offlineQueue = {
  list: async () => (await transact<OfflineReport[]>("readonly", (store) => store.getAll())).sort((a, b) => b.created_at_local.localeCompare(a.created_at_local)),
  put: (report: OfflineReport) => transact("readwrite", (store) => store.put(report)),
  remove: (id: string) => transact("readwrite", (store) => store.delete(id)),
};

export async function syncQueuedReports(force = false): Promise<{ synced: number; failed: number }> {
  const reports = await offlineQueue.list();
  let synced = 0; let failed = 0;
  for (const report of reports) {
    if (!force && report.next_retry_at && new Date(report.next_retry_at) > new Date()) continue;
    const syncing = { ...report, sync_status: "SYNCING" as const, last_error: undefined };
    await offlineQueue.put(syncing);
    try {
      await api.createRequest({ ...report.form_data, source: "OFFLINE_SYNC", client_submission_id: report.client_submission_id, received_at: report.created_at_local, raw_payload: { offline_local_id: report.local_id, offline_created_at_local: report.created_at_local } });
      await offlineQueue.remove(report.local_id);
      synced += 1;
    } catch (error) {
      const retryCount = report.retry_count + 1;
      const delaySeconds = Math.min(300, 2 ** Math.min(retryCount, 8));
      await offlineQueue.put({ ...report, sync_status: "FAILED", retry_count: retryCount, last_error: error instanceof Error ? error.message : "Không thể đồng bộ", next_retry_at: new Date(Date.now() + delaySeconds * 1000).toISOString() });
      failed += 1;
    }
  }
  return { synced, failed };
}
