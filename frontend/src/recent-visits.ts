/** Pure recent-visit data helpers; safe for both the entry and lazy modules. */
export interface RecentVisitEntry {
  key: string;
  name: string;
  href: string;
}

export function normalizeRecentVisits(value: unknown, limit = 4): RecentVisitEntry[] {
  if (!Array.isArray(value)) return [];
  const seen = new Set<string>();
  const entries: RecentVisitEntry[] = [];
  for (const candidate of value) {
    if (!candidate || typeof candidate !== "object") continue;
    const raw = candidate as Record<string, unknown>;
    if (typeof raw.key !== "string" || typeof raw.name !== "string" || typeof raw.href !== "string") continue;
    const key = raw.key.trim();
    const name = raw.name.trim();
    const href = raw.href.trim();
    if (!key || !name || !href || seen.has(key)) continue;
    seen.add(key);
    entries.push({ key, name, href });
    if (entries.length >= limit) break;
  }
  return entries;
}
