import Link from "next/link";
import { notFound } from "next/navigation";
import { IntervalBar } from "@/components/IntervalBar";
import { type EvaluationDetail, type MetricSummary, STATIC_EXPORT, dynamicUnlessStatic, serverGet } from "@/lib/api";
import { dateFr, interval, num, shortCommit } from "@/lib/format";

const OPS: Record<string, string> = {
  S1_youden: "Seuil S1 : maximise sensibilité + spécificité sur la validation",
  S2_sens95: "Seuil S2 : sensibilité d'au moins 95 % sur la validation (scénario de dépistage)",
};

const RATIOS: [string, string][] = [
  ["sensitivity", "Sensibilité"],
  ["specificity", "Spécificité"],
  ["precision", "Précision"],
  ["f1", "F1"],
];

function MetricLine({ label, m, axis }: { label: string; m: MetricSummary | undefined; axis?: [number, number] }) {
  return (
    <tr className="border-t border-rule align-middle">
      <th scope="row" className="py-2.5 pr-4 text-left font-normal">{label}</th>
      <td className="py-2.5 pr-4">
        <IntervalBar
          label={label}
          mean={m?.mean ?? null}
          low={m?.ci_low ?? null}
          high={m?.ci_high ?? null}
          min={axis?.[0] ?? 0}
          max={axis?.[1] ?? 1}
        />
      </td>
      <td className="py-2.5 pr-4 text-sm tabular-nums">{interval(m?.mean, m?.ci_low, m?.ci_high)}</td>
      <td className="text-muted py-2.5 text-sm tabular-nums">{m?.std_across_seeds == null ? "" : `± ${num(m.std_across_seeds)}`}</td>
    </tr>
  );
}

function Table({ caption, axis, children }: { caption: string; axis: string; children: React.ReactNode }) {
  return (
    <table className="w-full text-left">
      <caption className="sr-only">{caption}</caption>
      <thead className="text-muted text-sm">
        <tr>
          <th scope="col" className="pb-2 pr-4 font-normal">Mesure</th>
          <th scope="col" className="pb-2 pr-4 font-normal">Intervalle (axe {axis})</th>
          <th scope="col" className="pb-2 pr-4 font-normal">Estimation [intervalle à 95 %]</th>
          <th scope="col" className="pb-2 font-normal">Écart entre seeds</th>
        </tr>
      </thead>
      <tbody>{children}</tbody>
    </table>
  );
}

export default async function EvaluationPage({ params }: { params: Promise<{ runId: string }> }) {
  await dynamicUnlessStatic();
  const { runId } = await params;
  const data = await serverGet<EvaluationDetail>(`/evaluations/${encodeURIComponent(runId)}`);
  if (!data) notFound();
  const { report: r, summary: s } = data;
  const agg = r.aggregate;
  const ops = Object.keys(r.seeds[0]?.operating_points ?? {});

  return (
    <div className="space-y-12">
      <section className="max-w-[68ch]">
        <p className="text-muted text-sm">
          <Link href="/" className="underline underline-offset-4">Évaluations</Link>
        </p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight">{r.model_id}</h1>
        <p className="text-muted mt-1 text-sm">
          Exécuté le {dateFr(r.created_at)}, protocole {r.protocol_version}, {s.n_seeds} seeds, images {s.size}×{s.size}
        </p>
        <p className="mt-2 text-sm">
          <Link href={`/evaluations/${encodeURIComponent(runId)}/analyses`} className="underline underline-offset-4">
            Analyses complémentaires : comparaison, calibration, robustesse, sanité Grad-CAM
          </Link>
        </p>
        {!s.is_reference && (
          <div role="note" className="bg-warn-bg text-warn mt-4 px-3 py-2 text-sm">
            <p>Cette exécution n&apos;est pas un résultat de référence. Ne pas la citer comme performance.</p>
            <ul className="mt-1 list-disc pl-5">
              {s.train_subset ? <li>Entraînement sur un sous-échantillon de {s.train_subset} images.</li> : null}
              {s.size !== 224 ? <li>Résolution {s.size}×{s.size} au lieu de 224×224.</li> : null}
              {s.dirty ? <li>Dépôt modifié au moment de l&apos;exécution.</li> : null}
            </ul>
          </div>
        )}
      </section>

      <section>
        <h2 className="mb-1 text-xl font-semibold">Discrimination sur le jeu de test</h2>
        <p className="text-muted mb-4 max-w-[68ch] text-sm">
          Moyenne des seeds. L&apos;intervalle est un bootstrap à 95 % sur les images de test ; l&apos;écart entre seeds mesure
          la variabilité de l&apos;entraînement.
        </p>
        <Table caption="AUC ROC et AUC précision-rappel" axis="0,5 à 1">
          <MetricLine label="AUC ROC" m={agg["auc"]} axis={[0.5, 1]} />
          <MetricLine label="AUC précision-rappel" m={agg["auc_pr"]} axis={[0.5, 1]} />
        </Table>
      </section>

      {ops.map((op) => (
        <section key={op}>
          <h2 className="mb-1 text-xl font-semibold">{OPS[op] ?? op}</h2>
          <p className="text-muted mb-4 max-w-[68ch] text-sm">
            Seuil choisi sur la validation de chaque seed, appliqué au test sans modification. La prévalence de
            pneumonie est plus faible dans le test que dans la validation : la précision et le F1 ne se comparent pas
            directement entre les deux.
          </p>
          <Table caption={OPS[op] ?? op} axis="0 à 1">
            {RATIOS.map(([k, label]) => (
              <MetricLine key={k} label={label} m={agg[`${op}/${k}`]} />
            ))}
          </Table>
          <dl className="mt-4 flex gap-8 text-sm">
            <div>
              <dt className="text-muted">Faux positifs (moyenne par seed)</dt>
              <dd className="text-lg tabular-nums">{num(agg[`${op}/fp`]?.mean, 1)}</dd>
            </div>
            <div>
              <dt className="text-muted">Faux négatifs (moyenne par seed)</dt>
              <dd className="text-lg tabular-nums">{num(agg[`${op}/fn`]?.mean, 1)}</dd>
            </div>
          </dl>
        </section>
      ))}

      <section>
        <h2 className="mb-1 text-xl font-semibold">Calibration</h2>
        <p className="text-muted mb-4 max-w-[68ch] text-sm">
          Plus la valeur est proche de 0, mieux les probabilités annoncées correspondent aux fréquences observées.
          Aucune recalibration n&apos;est appliquée ici.
        </p>
        <Table caption="Brier et ECE" axis="0 à 0,5">
          <MetricLine label="Score de Brier" m={agg["brier"]} axis={[0, 0.5]} />
          <MetricLine label="ECE (10 intervalles)" m={agg["ece_10"]} axis={[0, 0.5]} />
        </Table>
      </section>

      <section>
        <h2 className="mb-3 text-xl font-semibold">Résultat de chaque seed</h2>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[32rem] text-left text-sm tabular-nums">
            <caption className="sr-only">Résultats par seed</caption>
            <thead className="text-muted">
              <tr>
                <th scope="col" className="pb-2 pr-4 font-normal">Seed</th>
                <th scope="col" className="pb-2 pr-4 font-normal">Meilleure epoch</th>
                <th scope="col" className="pb-2 pr-4 font-normal">AUC validation</th>
                <th scope="col" className="pb-2 pr-4 font-normal">AUC test</th>
                {ops.map((op) => (
                  <th key={op} scope="col" className="pb-2 pr-4 font-normal">Seuil {op.split("_")[0]}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {r.seeds.map((sd) => (
                <tr key={sd.seed} className="border-t border-rule">
                  <th scope="row" className="py-2 pr-4 text-left font-normal">{sd.seed}</th>
                  <td className="py-2 pr-4">{sd.best_epoch}</td>
                  <td className="py-2 pr-4">{num(sd.val_auc)}</td>
                  <td className="py-2 pr-4">{num(sd.test_auc)}</td>
                  {ops.map((op) => (
                    <td key={op} className="py-2 pr-4">{num(sd.operating_points[op]?.threshold)}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="max-w-[68ch]">
        <h2 className="mb-3 text-xl font-semibold">Limites de cette évaluation</h2>
        <ul className="list-disc space-y-2 pl-5">
          {r.notes.map((n) => (
            <li key={n}>{n}</li>
          ))}
        </ul>
        <p className="mt-3">
          <Link href="/limites" className="underline underline-offset-4">Voir les limites des données</Link>
        </p>
      </section>

      <section>
        <h2 className="mb-3 text-xl font-semibold">Provenance</h2>
        <dl className="grid max-w-3xl grid-cols-[max-content_1fr] gap-x-6 gap-y-1.5 text-sm">
          <dt className="text-muted">Identifiant du rapport</dt><dd className="break-all">{r.run_id}</dd>
          <dt className="text-muted">Commit</dt><dd>{shortCommit(r.provenance.commit)}{r.provenance.dirty ? " (modifié)" : ""}</dd>
          <dt className="text-muted">Configuration (SHA-256)</dt><dd className="break-all">{r.provenance.config_hash}</dd>
          <dt className="text-muted">Données (SHA-256)</dt><dd className="break-all">{r.provenance.dataset_sha256}</dd>
          <dt className="text-muted">Matériel</dt><dd>{r.provenance.device}{r.provenance.gpu_name ? `, ${r.provenance.gpu_name}` : ""}</dd>
          <dt className="text-muted">Logiciel</dt><dd>Python {r.provenance.python}, PyTorch {r.provenance.torch}</dd>
        </dl>
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
