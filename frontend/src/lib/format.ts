/** Display formatting only. No business logic, no verdict derivation. */

/** Hashes are 64 hex chars; show enough to be checkable by eye without
 *  swallowing a table row. Full value always stays available via title/copy. */
export function abbreviateHash(hash: string, head = 10, tail = 6): string {
  if (hash.length <= head + tail + 1) return hash;
  return `${hash.slice(0, head)}…${hash.slice(-tail)}`;
}

export function formatPercent(value: number, digits = 0): string {
  return `${(value * 100).toFixed(digits)}%`;
}

/** ISO timestamp -> "2026-09-07 14:32 UTC". Keeps ISO ordering (sortable,
 *  unambiguous) rather than a locale format that reorders day and month. */
export function formatTimestamp(iso: string | null | undefined): string {
  if (!iso) return "—";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  const pad = (n: number) => String(n).padStart(2, "0");
  return (
    `${date.getUTCFullYear()}-${pad(date.getUTCMonth() + 1)}-${pad(date.getUTCDate())} ` +
    `${pad(date.getUTCHours())}:${pad(date.getUTCMinutes())} UTC`
  );
}

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  return iso.slice(0, 10);
}

/** An absent value must never render as "0", "false" or an empty cell that
 *  looks like a successful read. */
export function formatValue(value: unknown): string {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  return String(value);
}

export function formatQuantity(
  value: number | null | undefined,
  unit: string | null | undefined,
): string {
  if (value === null || value === undefined) return "—";
  return unit ? `${value} ${unit}` : String(value);
}

export function formatRupees(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return `₹${value.toFixed(2)}`;
}

/** Nx2 pixel point list -> SVG `points` attribute. */
export function polygonToPoints(polygon: [number, number][]): string {
  return polygon.map(([x, y]) => `${x},${y}`).join(" ");
}

export function truncate(text: string, max = 80): string {
  return text.length <= max ? text : `${text.slice(0, max - 1)}…`;
}
