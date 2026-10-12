/** Mise en forme française. Une valeur absente n'est jamais remplacée par un chiffre par défaut. */

export const NOT_AVAILABLE = "non disponible";

export function num(v: number | null | undefined, digits = 3): string {
  if (v === null || v === undefined || Number.isNaN(v)) return NOT_AVAILABLE;
  return v.toLocaleString("fr-FR", { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

export function interval(
  mean: number | null | undefined,
  low: number | null | undefined,
  high: number | null | undefined,
  digits = 3,
): string {
  if (mean === null || mean === undefined) return NOT_AVAILABLE;
  const m = num(mean, digits);
  if (low === null || low === undefined || high === null || high === undefined) return m;
  return `${m} [${num(low, digits)} ; ${num(high, digits)}]`;
}

export function shortCommit(c: string): string {
  return c.slice(0, 7);
}

export function dateFr(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("fr-FR", { year: "numeric", month: "long", day: "numeric", timeZone: "UTC" });
}
