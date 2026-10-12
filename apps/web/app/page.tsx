import Link from "next/link";
import { IntervalBar } from "@/components/IntervalBar";
import { type EvaluationSummary, serverGet, serverReachable } from "@/lib/api";
import { dateFr, interval, shortCommit } from "@/lib/format";

export const dynamic = "force-dynamic";

function Row({ e }: { e: EvaluationSummary }) {
  return (
    <tr className="border-t border-rule align-middle">
      <td className="py-3 pr-4">
        <Link href={`/evaluations/${e.run_id}`} className="font-medium underline underline-offset-4">
          {e.model_id}
        </Link>
        <div className="text-muted text-xs">
          {dateFr(e.created_at)}, {e.n_seeds} seeds, {e.size}×{e.size}, commit {shortCommit(e.commit)}
        </div>
      </td>
      <td className="py-3 pr-4">
        <IntervalBar
          label={`AUC de ${e.model_id}`}
          mean={e.auc?.mean ?? null}
          low={e.auc?.ci_low ?? null}
          high={e.auc?.ci_high ?? null}
          reference={{ value: 0.5, label: "Niveau du hasard (AUC = 0,5)" }}
        />
      </td>
      <td className="py-3 text-sm tabular-nums">{interval(e.auc?.mean, e.auc?.ci_low, e.auc?.ci_high)}</td>
    </tr>
  );
}

function Table({ rows }: { rows: EvaluationSummary[] }) {
  return (
    <table className="w-full text-left">
      <caption className="sr-only">AUC sur le jeu de test, moyenne des seeds et intervalle de confiance à 95 %</caption>
      <thead className="text-muted text-sm">
        <tr>
          <th scope="col" className="pb-2 pr-4 font-normal">Modèle</th>
          <th scope="col" className="pb-2 pr-4 font-normal">AUC entre 0,5 (hasard) et 1</th>
          <th scope="col" className="pb-2 font-normal">Estimation [intervalle à 95 %]</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((e) => (
          <Row key={e.run_id} e={e} />
        ))}
      </tbody>
    </table>
  );
}

export default async function Home() {
  const reachable = await serverReachable();
  const data = reachable ? await serverGet<{ items: EvaluationSummary[] }>("/evaluations") : null;
  const items = data?.items ?? [];
  const reference = items.filter((e) => e.is_reference);
  const other = items.filter((e) => !e.is_reference);

  return (
    <div className="space-y-12">
      <section className="max-w-[68ch]">
        <h1 className="text-3xl font-semibold tracking-tight">
          Des modèles d&apos;imagerie médicale comparés avec leur incertitude
        </h1>
        <p className="mt-4">
          MedAI Lab entraîne plusieurs modèles sur des radiographies thoraciques publiques, puis mesure leurs
          performances selon un protocole fixé à l&apos;avance. Chaque chiffre vient d&apos;un rapport d&apos;évaluation
          généré par le pipeline, avec son intervalle de confiance et sa provenance.
        </p>
      </section>

      {!reachable && (
        <section aria-live="polite" className="max-w-[68ch]">
          <h2 className="text-xl font-semibold">Le service d&apos;évaluation ne répond pas</h2>
          <p className="mt-2">
            L&apos;interface n&apos;affiche aucun résultat sans rapport source. Démarrez l&apos;API
            (<code>docker compose up</code>) puis rechargez la page.
          </p>
        </section>
      )}

      {reachable && items.length === 0 && (
        <section aria-live="polite" className="max-w-[68ch]">
          <h2 className="text-xl font-semibold">Aucune évaluation disponible</h2>
          <p className="mt-2">
            Aucun rapport valide n&apos;a été trouvé dans le dossier <code>reports/</code>. Lancez un entraînement avec{" "}
            <code>python -m medai_ml run --config ml/configs/resnet18.yaml</code> ou utilisez le notebook{" "}
            <code>notebooks/colab_train.ipynb</code>, puis copiez le dossier du rapport dans <code>reports/</code>.
          </p>
        </section>
      )}

      {reference.length > 0 && (
        <section>
          <h2 className="mb-1 text-xl font-semibold">Résultats de référence</h2>
          <p className="text-muted mb-4 max-w-[68ch] text-sm">
            Entraînement complet à 224×224, dépôt sans modification. Le jeu de test n&apos;est utilisé qu&apos;une fois par
            seed.
          </p>
          <Table rows={reference} />
        </section>
      )}

      {other.length > 0 && (
        <section>
          <h2 className="mb-1 text-xl font-semibold">Autres exécutions</h2>
          <p className="text-muted mb-4 max-w-[68ch] text-sm">
            Tests de fumée, sous-échantillons, résolutions réduites ou dépôt modifié. Ne pas citer comme performance.
          </p>
          <Table rows={other} />
        </section>
      )}
    </div>
  );
}
