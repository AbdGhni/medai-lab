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

/** Export statique (D01) : pages générées au build à partir de l'API locale, sans backend d'inférence. */
export const STATIC_EXPORT = process.env.NEXT_PUBLIC_STATIC_EXPORT === "1";
const FETCH_CACHE: RequestCache = STATIC_EXPORT ? "force-cache" : "no-store";

/** Rend la page dynamique hors export statique (les rapports sont lus à chaque requête). */
export async function dynamicUnlessStatic(): Promise<void> {
  if (!STATIC_EXPORT) {
    const { connection } = await import("next/server");
    await connection();
  }
}

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
    const res = await fetch(`${SERVER_BASE}${path}`, { cache: FETCH_CACHE });
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
    const res = await fetch(`${SERVER_BASE}/health`, { cache: FETCH_CACHE });
    return res.ok;
  } catch {
    return false;
  }
}

// ---- Analyses complémentaires (lues dans reports/<run_id>/analyses/, jamais calculées ici)

export interface AnalysisList {
  items: { name: string; created_at: string }[];
}

export interface Ci {
  mean: number | null;
  ci_low: number | null;
  ci_high: number | null;
}

export interface ComparisonRow {
  model: string;
  run_id: string;
  auc_model: number;
  auc_baseline: number;
  auc_diff_model_minus_baseline: number;
  ci95: [number, number];
  ci_adjusted: [number, number];
  p_bootstrap: number;
  p_holm: number;
  established: boolean;
  wording: string;
  delong_on_seed_mean: { auc_diff: number; p: number };
  mcnemar_s1_on_seed_mean: { a_only_correct: number; b_only_correct: number; p: number };
}

export interface ComparisonAnalysis {
  baseline: { model: string; run_id: string };
  n_boot: number;
  n_comparisons: number;
  comparisons: ComparisonRow[];
  notes: string[];
}

export interface ReliabilityPoint {
  bin: number;
  n: number;
  mean_prob: number;
  observed_freq: number;
}

export interface CalibrationAnalysis {
  per_seed: { seed: number; temperature: number; temperature_at_bound?: boolean }[];
  mean_over_seeds: Record<string, number>;
  reliability_before_seed0: ReliabilityPoint[];
  reliability_after_seed0: ReliabilityPoint[];
  method: string;
}

export interface RobustnessAnalysis {
  n_boot: number;
  n_seeds: number;
  thresholds_note: string;
  clean: Record<string, Ci>;
  perturbations: Record<string, { level: number; metrics: Record<string, Ci> }[]>;
}

export interface SanityAnalysis {
  model_id: string;
  passes_all_seeds: boolean | null;
  per_seed: {
    seed: number;
    passes: boolean | null;
    threshold_rank_corr: number;
    rows: { fraction_randomized: number; rank_corr_mean: number | null; ssim_mean: number | null; n_valid_images: number; n_excluded_base_constant: number; n_randomized_constant: number }[];
  }[];
}
