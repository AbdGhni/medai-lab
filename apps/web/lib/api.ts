// Accès à l'API. Les composants serveur appellent API_URL ; le navigateur passe par /api.

export interface MetricSummary {
  mean: number | null;
  std_across_seeds: number | null;
  ci_low: number | null;
  ci_high: number | null;
  n_boot_valid: number;
}

export interface OperatingPoint {
  threshold: number;
  metrics: Record<string, number | null>;
}

export interface SeedResult {
  seed: number;
  best_epoch: number;
  val_auc: number | null;
  test_auc: number | null;
  test_auc_pr: number | null;
  test_brier: number;
  test_ece_10: number;
  operating_points: Record<string, OperatingPoint>;
}

export interface Provenance {
  commit: string;
  dirty: boolean;
  config_hash: string;
  dataset_sha256: string;
  python: string;
  torch: string;
  platform: string;
  device: string;
  gpu_name: string | null;
}

export interface EvaluationReport {
  run_id: string;
  model_id: string;
  created_at: string;
  protocol_version: string;
  disclaimer: string;
  config: Record<string, unknown>;
  provenance: Provenance;
  dataset: Record<string, unknown>;
  seeds: SeedResult[];
  aggregate: Record<string, MetricSummary>;
  notes: string[];
}

export interface EvaluationSummary {
  run_id: string;
  model_id: string;
  created_at: string;
  n_seeds: number;
  size: number;
  auc: { mean: number | null; ci_low: number | null; ci_high: number | null } | null;
  is_reference: boolean;
  dirty: boolean;
  train_subset: number | null;
  commit: string;
}

export interface EvaluationDetail {
  report: EvaluationReport;
  summary: EvaluationSummary;
}

export interface GalleryItem {
  id: string;
  label: number;
  label_name: string;
}

export interface Gallery {
  license: string;
  attribution: string;
  selection: string;
  items: GalleryItem[];
}

const SERVER_BASE = process.env.API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
  }
}

/** Appel côté serveur. Renvoie null si le service est injoignable (la page l'explique). */
export async function serverGet<T>(path: string): Promise<T | null> {
  try {
    const res = await fetch(`${SERVER_BASE}${path}`, { cache: "no-store" });
    if (res.status === 404) return null;
    if (!res.ok) throw new ApiError(`API ${res.status}`, res.status);
    return (await res.json()) as T;
  } catch (e) {
    if (e instanceof ApiError) throw e;
    return null;
  }
}

export async function serverReachable(): Promise<boolean> {
  try {
    const res = await fetch(`${SERVER_BASE}/health`, { cache: "no-store" });
    return res.ok;
  } catch {
    return false;
  }
}
