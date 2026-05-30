import {
  loadPacketIds,
  loadRealCasePacketIds,
  loadReviewState,
  PACKET_STORAGE_KEY,
  REAL_CASE_PACKET_KEY,
  REVIEW_STORAGE_KEY,
  savePacketIds,
  saveRealCasePacketIds,
  saveReviewState,
  type ReviewRecord,
} from "./detentionReview";

const DB_NAME = "benchassist-detention-review";
const DB_VERSION = 1;
const STORE = "state";
const BACKUP_KEY = "auto_backup";

export interface ReviewStorageSnapshot {
  reviewState: Record<string, ReviewRecord>;
  packetIds: string[];
  realCasePacketIds: string[];
  savedAt: string;
}

function openDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    if (typeof indexedDB === "undefined") {
      reject(new Error("indexedDB unavailable"));
      return;
    }
    const req = indexedDB.open(DB_NAME, DB_VERSION);
    req.onerror = () => reject(req.error ?? new Error("indexedDB open failed"));
    req.onupgradeneeded = () => {
      req.result.createObjectStore(STORE);
    };
    req.onsuccess = () => resolve(req.result);
  });
}

async function idbGet<T>(key: string): Promise<T | null> {
  try {
    const db = await openDb();
    return await new Promise((resolve, reject) => {
      const tx = db.transaction(STORE, "readonly");
      const req = tx.objectStore(STORE).get(key);
      req.onerror = () => reject(req.error);
      req.onsuccess = () => resolve((req.result as T | undefined) ?? null);
    });
  } catch {
    return null;
  }
}

async function idbSet(key: string, value: unknown): Promise<void> {
  const db = await openDb();
  await new Promise<void>((resolve, reject) => {
    const tx = db.transaction(STORE, "readwrite");
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
    tx.objectStore(STORE).put(value, key);
  });
}

export async function hydrateReviewStorageFromIndexedDb(): Promise<ReviewStorageSnapshot | null> {
  const snap = await idbGet<ReviewStorageSnapshot>(BACKUP_KEY);
  if (!snap?.reviewState) return null;
  return snap;
}

export async function persistReviewStorageSnapshot(snapshot: ReviewStorageSnapshot): Promise<void> {
  await idbSet(BACKUP_KEY, snapshot);
  saveReviewState(snapshot.reviewState);
  savePacketIds(snapshot.packetIds);
  saveRealCasePacketIds(snapshot.realCasePacketIds);
  localStorage.setItem(REVIEW_STORAGE_KEY, JSON.stringify(snapshot.reviewState));
  localStorage.setItem(PACKET_STORAGE_KEY, JSON.stringify(snapshot.packetIds));
  localStorage.setItem(REAL_CASE_PACKET_KEY, JSON.stringify(snapshot.realCasePacketIds));
}

export function buildReviewStorageSnapshot(
  reviewState: Record<string, ReviewRecord>,
  packetIds: string[],
  realCasePacketIds: string[],
): ReviewStorageSnapshot {
  return {
    reviewState,
    packetIds,
    realCasePacketIds,
    savedAt: new Date().toISOString(),
  };
}

export async function loadReviewStorageWithFallback(): Promise<ReviewStorageSnapshot> {
  const fromIdb = await hydrateReviewStorageFromIndexedDb();
  if (fromIdb) return fromIdb;
  return {
    reviewState: loadReviewState(),
    packetIds: loadPacketIds(),
    realCasePacketIds: loadRealCasePacketIds(),
    savedAt: new Date(0).toISOString(),
  };
}

let autoBackupTimer: ReturnType<typeof setTimeout> | null = null;

export function scheduleReviewStorageBackup(
  reviewState: Record<string, ReviewRecord>,
  packetIds: string[],
  realCasePacketIds: string[],
  delayMs = 1500,
): void {
  if (typeof window === "undefined") return;
  if (autoBackupTimer) clearTimeout(autoBackupTimer);
  autoBackupTimer = setTimeout(() => {
    void persistReviewStorageSnapshot(buildReviewStorageSnapshot(reviewState, packetIds, realCasePacketIds));
  }, delayMs);
}
