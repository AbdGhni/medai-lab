import Link from "next/link";
import { notFound } from "next/navigation";
import { ReliabilityPlot } from "@/components/ReliabilityPlot";
import {
  type DomainShiftAnalysis,
  type AnalysisList,
  type CalibrationAnalysis,
  type Ci,
  type ComparisonAnalysis,
  type EvaluationDetail,
  type RobustnessAnalysis,
  type SanityAnalysis,
  STATIC_EXPORT, dynamicUnlessStatic, serverGet,
} from "@/lib/api";
import { interval, num } from "@/lib/format";

const PERTURBATIONS: Record<string, { label: string; unit: string }> = {
  gaussian_noise: { label: "Bruit gaussien", unit: "écart-type" },
  gaussian_blur: { label: "Flou gaussien", unit: "sigma (pixels)" },
  brightness: { label: "Luminosité", unit: "facteur" },
  contrast: { label: "Contraste", unit: "facteur" },
  jpeg: { label: "Compression JPEG", unit: "qualité" },
  rotation: { label: "Rotation", unit: "degrés" },
};

const ROB_COLUMNS: [string, string][] = [
  ["auc", "AUC ROC"],
  ["S1_youden/sensitivity", "Sensibilité (S1)"],
  ["S1_youden/specificity", "Spécificité (S1)"],
  ["S2_sens95/sensitivity", "Sensibilité (S2)"],
  ["S2_sens95/specificity", "Spécificité (S2)"],
];

const TARGET_LABELS: Record<string, string> = {
  pneumonia_vs_all: "Pneumonie contre toutes les autres images (cible principale)",
  pneumonia_vs_no_finding: "Pneumonie contre images sans anomalie (cible secondaire)",
};

const SHIFT_ROWS: [string, string][] = [
  ["auc", "AUC ROC"],
  ["auc_pr", "AUC précision-rappel"],
  ["S1_youden/sensitivity", "Sensibilité (S1)"],
  ["S1_youden/specificity", "Spécificité (S1)"],
  ["S1_youden/flagged_rate", "Part d'images signalées (S1)"],
  ["S2_sens95/sensitivity", "Sensibilité (S2)"],
  ["S2_sens95/specificity", "Spécificité (S2)"],
  ["S2_sens95/flagged_rate", "Part d'images signalées (S2)"],
];

const CAL_ROWS: [string, string, string][] = [
  ["ece10", "ECE (10 intervalles)", "ece10"],
  ["ece_adaptive", "ECE (effectifs égaux)", "ece_adaptive"],
  ["brier", "Score de Brier", "brier"],
  ["nll", "Log-vraisemblance négative", "nll"],
];

function Missing({ what }: { what: string }) {
  return (
    <p className="text-muted max-w-[68ch] text-sm">
      {what} n&apos;a pas été exécutée pour cette évaluation. Aucune valeur n&apos;est affichée.
    </p>
  );
}

function cell(c: Ci | undefined) {
  return c ? interval(c.mean, c.ci_low, c.ci_high) : "non disponible";
}

export default async function AnalysesPage({ params }: { params: Promise<{ runId: string }> }) {
  await dynamicUnlessStatic();
  const { runId } = await params;
  const base = `/evaluations/${encodeURIComponent(runId)}`;
  const detail = await serverGet<EvaluationDetail>(base);
  if (!detail) notFound();
  const list = (await serverGet<AnalysisList>(`${base}/analyses`))?.items ?? [];
  const has = (n: string) => list.some((a) => a.name === n);
  const [comparison, calibration, robustness, sanity, shift] = await Promise.all([
    has("comparison") ? serverGet<ComparisonAnalysis>(`${base}/analyses/comparison`) : null,
    has("calibration") ? serverGet<CalibrationAnalysis>(`${base}/analyses/calibration`) : null,
    has("robustness") ? serverGet<RobustnessAnalysis>(`${base}/analyses/robustness`) : null,
    has("gradcam_sanity") ? serverGet<SanityAnalysis>(`${base}/analyses/gradcam_sanity`) : null,
    has("domain_shift") ? serverGet<DomainShiftAnalysis>(`${base}/analyses/domain_shift`) : null,
  ]);
  const { summary: s } = detail;

  return (
    <div className="space-y-12">
      <section className="max-w-[68ch]">
        <p className="text-muted text-sm">
          <Link href="/" className="underline underline-offset-4">Évaluations</Link>
          {" / "}
          <Link href={`/evaluations/${encodeURIComponent(runId)}`} className="underline underline-offset-4">
            {detail.report.model_id}
          </Link>
        </p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight">Analyses complémentaires</h1>
        <p className="text-muted mt-1 text-sm">
          Calculées à partir des prédictions et des poids archivés de l&apos;évaluation {detail.report.model_id}, jamais
          dans le navigateur. Les seuils S1 et S2 sont ceux fixés sur la validation.
        </p>
        {!s.is_reference && (
          <div role="note" className="bg-warn-bg text-warn mt-4 px-3 py-2 text-sm">
            Cette exécution n&apos;est pas un résultat de référence. Ne pas citer ces chiffres comme performance.
          </div>
        )}
      </section>

      <section>
        <h2 className="mb-1 text-xl font-semibold">Comparaison avec le modèle de référence</h2>
        {comparison ? (
          <>
            <p className="text-muted mb-4 max-w-[68ch] text-sm">
              Référence : {comparison.baseline.model}. Différence d&apos;AUC (modèle moins référence), bootstrap apparié
              sur {comparison.n_boot} réplicats ; p-valeurs corrigées par Holm pour {comparison.n_comparisons}{" "}
              comparaison(s). Une p-valeur se lit avec la différence et son intervalle.
            </p>
            <table className="w-full text-left text-sm">
              <caption className="sr-only">Comparaison des modèles avec la référence</caption>
              <thead className="text-muted">
                <tr>
                  <th scope="col" className="pb-2 pr-4 font-normal">Modèle</th>
                  <th scope="col" className="pb-2 pr-4 font-normal">Différence d&apos;AUC [intervalle à 95 %]</th>
                  <th scope="col" className="pb-2 pr-4 font-normal">p (Holm)</th>
                  <th scope="col" className="pb-2 font-normal">Conclusion</th>
                </tr>
              </thead>
              <tbody>
                {comparison.comparisons.map((c) => (
                  <tr key={c.run_id} className="border-rule border-t align-top">
                    <th scope="row" className="py-2.5 pr-4 text-left font-normal">{c.model}</th>
                    <td className="py-2.5 pr-4 tabular-nums">
                      {interval(c.auc_diff_model_minus_baseline, c.ci95[0], c.ci95[1])}
                    </td>
                    <td className="py-2.5 pr-4 tabular-nums">{num(c.p_holm)}</td>
                    <td className="py-2.5">{c.wording}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </>
        ) : (
          <Missing what="La comparaison statistique" />
        )}
      </section>

      <section>
        <h2 className="mb-1 text-xl font-semibold">Calibration</h2>
        {calibration ? (
          <>
            <p className="text-muted mb-4 max-w-[68ch] text-sm">
              {calibration.method}. Moyenne sur {calibration.per_seed.length} seeds, évaluée sur le test.
            </p>
            {calibration.per_seed.some((p) => p.temperature_at_bound) && (
              <div role="note" className="bg-warn-bg text-warn mb-4 max-w-[68ch] px-3 py-2 text-sm">
                La température ajustée atteint la limite de l&apos;intervalle de recherche pour au moins une seed : la
                validation est probablement trop séparable pour ajuster une température fiable.
              </div>
            )}
            <table className="text-left text-sm">
              <caption className="sr-only">Calibration avant et après temperature scaling</caption>
              <thead className="text-muted">
                <tr>
                  <th scope="col" className="pb-2 pr-6 font-normal">Mesure</th>
                  <th scope="col" className="pb-2 pr-6 font-normal">Avant</th>
                  <th scope="col" className="pb-2 font-normal">Après</th>
                </tr>
              </thead>
              <tbody>
                {CAL_ROWS.map(([key, label, prefix]) => (
                  <tr key={key} className="border-rule border-t">
                    <th scope="row" className="py-2 pr-6 text-left font-normal">{label}</th>
                    <td className="py-2 pr-6 tabular-nums">{num(calibration.mean_over_seeds[`${prefix}_before`])}</td>
                    <td className="py-2 tabular-nums">{num(calibration.mean_over_seeds[`${prefix}_after`])}</td>
                  </tr>
                ))}
                <tr className="border-rule border-t">
                  <th scope="row" className="py-2 pr-6 text-left font-normal">Température (par seed)</th>
                  <td colSpan={2} className="py-2 tabular-nums">
                    {calibration.per_seed.map((p) => `${p.seed} : ${num(p.temperature, 2)}`).join(" ; ")}
                  </td>
                </tr>
              </tbody>
            </table>
            <div className="mt-6 flex flex-wrap gap-8">
              <figure>
                <ReliabilityPlot label="Fiabilité avant calibration" points={calibration.reliability_before_seed0} />
                <figcaption className="text-muted mt-1 text-sm">Avant (seed 0)</figcaption>
              </figure>
              <figure>
                <ReliabilityPlot label="Fiabilité après calibration" points={calibration.reliability_after_seed0} />
                <figcaption className="text-muted mt-1 text-sm">Après (seed 0)</figcaption>
              </figure>
            </div>
          </>
        ) : (
          <Missing what="L'analyse de calibration" />
        )}
      </section>

      <section>
        <h2 className="mb-1 text-xl font-semibold">Robustesse aux perturbations</h2>
        {robustness ? (
          <>
            <p className="text-muted mb-4 max-w-[68ch] text-sm">
              Perturbations appliquées au jeu de test uniquement. {robustness.thresholds_note} Moyenne sur{" "}
              {robustness.n_seeds} seeds, intervalle bootstrap à 95 % ({robustness.n_boot} réplicats).
            </p>
            <div className="space-y-8">
              {Object.entries(robustness.perturbations).map(([kind, rows]) => (
                <div key={kind} className="overflow-x-auto">
                  <h3 className="mb-2 font-medium">
                    {PERTURBATIONS[kind]?.label ?? kind}{" "}
                    <span className="text-muted text-sm font-normal">({PERTURBATIONS[kind]?.unit ?? "niveau"})</span>
                  </h3>
                  <table className="w-full text-left text-sm">
                    <caption className="sr-only">{PERTURBATIONS[kind]?.label ?? kind}</caption>
                    <thead className="text-muted">
                      <tr>
                        <th scope="col" className="pb-2 pr-4 font-normal">Niveau</th>
                        {ROB_COLUMNS.map(([k, l]) => (
                          <th key={k} scope="col" className="pb-2 pr-4 font-normal">{l}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      <tr className="border-rule border-t">
                        <th scope="row" className="py-2 pr-4 text-left font-normal">Sans perturbation</th>
                        {ROB_COLUMNS.map(([k]) => (
                          <td key={k} className="py-2 pr-4 tabular-nums">{cell(robustness.clean[k])}</td>
                        ))}
                      </tr>
                      {rows.map((r) => (
                        <tr key={r.level} className="border-rule border-t">
                          <th scope="row" className="py-2 pr-4 text-left font-normal tabular-nums">
                            {r.level.toLocaleString("fr-FR")}
                          </th>
                          {ROB_COLUMNS.map(([k]) => (
                            <td key={k} className="py-2 pr-4 tabular-nums">{cell(r.metrics[k])}</td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ))}
            </div>
          </>
        ) : (
          <Missing what="L'analyse de robustesse" />
        )}
      </section>

      <section>
        <h2 className="mb-1 text-xl font-semibold">Test de sanité de Grad-CAM</h2>
        {sanity ? (
          <>
            <p className="max-w-[68ch] text-sm">
              {sanity.passes_all_seeds === true
                ? "Les cartes changent quand les poids sont randomisés, pour toutes les seeds. Cela ne démontre pas leur pertinence clinique."
                : sanity.passes_all_seeds === false
                  ? "Le test n'est pas réussi pour toutes les seeds : les cartes Grad-CAM ne sont pas fiables pour ce modèle."
                  : "Le test n'est pas concluant : trop peu d'images exploitables sur au moins une seed."}
            </p>
            <p className="text-muted mt-1 mb-4 max-w-[68ch] text-sm">
              Corrélation de rang et SSIM entre la carte du modèle entraîné et celle du modèle dont une fraction des
              couches, à partir de la sortie, est randomisée. Critère fixé avant exécution : corrélation de rang
              inférieure à {num(sanity.per_seed[0]?.threshold_rank_corr, 1)} à 100 % de randomisation.
            </p>
            <div className="space-y-6">
              {sanity.per_seed.map((ps) => (
                <table key={ps.seed} className="text-left text-sm">
                  <caption className="mb-1 text-left font-medium">
                    Seed {ps.seed} : {ps.passes === true ? "réussi" : ps.passes === false ? "non réussi" : "non concluant"}
                  </caption>
                  <thead className="text-muted">
                    <tr>
                      <th scope="col" className="pb-2 pr-6 font-normal">Couches randomisées</th>
                      <th scope="col" className="pb-2 pr-6 font-normal">Corrélation de rang</th>
                      <th scope="col" className="pb-2 pr-6 font-normal">SSIM</th>
                      <th scope="col" className="pb-2 font-normal">Images exploitables</th>
                    </tr>
                  </thead>
                  <tbody>
                    {ps.rows.map((r) => (
                      <tr key={r.fraction_randomized} className="border-rule border-t">
                        <th scope="row" className="py-2 pr-6 text-left font-normal tabular-nums">
                          {(r.fraction_randomized * 100).toLocaleString("fr-FR")} %
                        </th>
                        <td className="py-2 pr-6 tabular-nums">{num(r.rank_corr_mean)}</td>
                        <td className="py-2 pr-6 tabular-nums">{num(r.ssim_mean)}</td>
                        <td className="py-2 tabular-nums">
                          {r.n_valid_images} sur {r.n_valid_images + r.n_excluded_base_constant}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ))}
            </div>
          </>
        ) : (
          <Missing what="Le test de sanité" />
        )}
      </section>

      <section>
        <h2 className="mb-1 text-xl font-semibold">Décalage de domaine : ChestMNIST (exploratoire)</h2>
        {shift ? (
          <>
            <p className="max-w-[68ch] text-sm">
              Le modèle, entraîné sur PneumoniaMNIST (enfants, un centre), est appliqué sans modification à des
              radiographies d&apos;adultes ({shift.dataset.name}, {shift.dataset.size}×{shift.dataset.size},
              licence {shift.dataset.license}). Les seuils restent ceux fixés sur la validation de PneumoniaMNIST.
            </p>
            <p className="text-muted mt-1 mb-4 max-w-[68ch] text-sm">
              Exploratoire : la population, la définition du label (extraite automatiquement de comptes rendus) et la
              prévalence changent en même temps ; aucune cause unique ne peut être attribuée à la baisse. Moyenne sur{" "}
              {shift.n_seeds} seeds, intervalle bootstrap à 95 % ({shift.n_boot} réplicats).
            </p>
            <div className="space-y-6">
              {Object.entries(shift.targets).map(([name, t]) => (
                <table key={name} className="text-left text-sm">
                  <caption className="mb-1 text-left font-medium">
                    {TARGET_LABELS[name] ?? name} : {t.n_images} images, {t.n_positive} positives (prévalence{" "}
                    {(t.prevalence * 100).toLocaleString("fr-FR", { maximumFractionDigits: 2 })} %)
                  </caption>
                  <thead className="text-muted">
                    <tr>
                      <th scope="col" className="pb-2 pr-6 font-normal">Mesure</th>
                      <th scope="col" className="pb-2 font-normal">Estimation [intervalle à 95 %]</th>
                    </tr>
                  </thead>
                  <tbody>
                    {SHIFT_ROWS.map(([k, label]) => (
                      <tr key={k} className="border-rule border-t">
                        <th scope="row" className="py-2 pr-6 text-left font-normal">{label}</th>
                        <td className="py-2 tabular-nums">{cell(t.metrics[k])}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ))}
            </div>
          </>
        ) : (
          <Missing what="L'analyse de décalage de domaine" />
        )}
      </section>
    </div>
  );
}

async function staticParams(): Promise<{ runId: string }[]> {
  const data = await serverGet<{ items: { run_id: string }[] }>("/evaluations");
  return (data?.items ?? []).map((e) => ({ runId: e.run_id }));
}

// Défini seulement pour l'export statique : sinon la route doit rester entièrement dynamique.
export const generateStaticParams = STATIC_EXPORT ? staticParams : undefined;
