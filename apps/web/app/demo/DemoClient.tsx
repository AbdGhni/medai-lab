"use client";

import { useEffect, useState } from "react";
import type { EvaluationSummary, Gallery } from "@/lib/api";
import { num } from "@/lib/format";

interface Prediction {
  probability_pneumonia: number;
  operating_points: Record<string, { threshold: number; predicted_pneumonia: boolean }>;
  ground_truth_label: number;
  seed: number;
  resized_from: number | null;
}

interface Explanation {
  probability_pneumonia: number;
  overlay_png_base64: string;
  method: string;
  sanity_checked: boolean;
  sanity_passed: boolean | null;
  note: string;
}

const LABEL = { 0: "normal", 1: "pneumonie" } as const;

async function call<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`/api${path}`, {
    method: body ? "POST" : "GET",
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    let detail = `Erreur ${res.status}`;
    try {
      const j = await res.json();
      if (typeof j.detail === "string") detail = j.detail;
    } catch {
      /* corps non JSON */
    }
    throw new Error(detail);
  }
  return (await res.json()) as T;
}

export function DemoClient() {
  const [gallery, setGallery] = useState<Gallery | null>(null);
  const [runs, setRuns] = useState<EvaluationSummary[]>([]);
  const [runId, setRunId] = useState("");
  const [imageId, setImageId] = useState("");
  const [pred, setPred] = useState<Prediction | null>(null);
  const [expl, setExpl] = useState<Explanation | null>(null);
  const [busy, setBusy] = useState<"predict" | "explain" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    let alive = true;
    Promise.all([call<Gallery>("/gallery"), call<{ items: EvaluationSummary[] }>("/evaluations")])
      .then(([g, e]) => {
        if (!alive) return;
        setGallery(g);
        setRuns(e.items);
        setRunId(e.items[0]?.run_id ?? "");
        setImageId(g.items[0]?.id ?? "");
      })
      .catch((e: Error) => alive && setError(e.message))
      .finally(() => alive && setLoaded(true));
    return () => {
      alive = false;
    };
  }, []);

  function reset() {
    setPred(null);
    setExpl(null);
    setError(null);
  }

  async function run(kind: "predict" | "explain") {
    setBusy(kind);
    setError(null);
    try {
      if (kind === "predict") setPred(await call<Prediction>("/predict", { run_id: runId, image_id: imageId }));
      else setExpl(await call<Explanation>("/explain", { run_id: runId, image_id: imageId }));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(null);
    }
  }

  if (!loaded) return <p aria-live="polite">Chargement des images d&apos;exemple…</p>;
  if (!gallery || gallery.items.length === 0)
    return (
      <p aria-live="polite" className="max-w-[68ch]">
        Aucune image d&apos;exemple disponible. Générez la galerie avec <code>python -m medai_ml gallery</code>, ou démarrez
        l&apos;API.
      </p>
    );
  if (runs.length === 0)
    return (
      <p aria-live="polite" className="max-w-[68ch]">
        Aucune évaluation disponible : sans modèle évalué, il n&apos;y a rien à essayer. Entraînez un modèle (voir la page
        Évaluations).
      </p>
    );

  const selected = runs.find((r) => r.run_id === runId);

  return (
    <div className="grid gap-10 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
      <div className="space-y-6">
        <div>
          <label htmlFor="run" className="text-muted mb-1 block text-sm">Modèle évalué</label>
          <select
            id="run"
            value={runId}
            onChange={(e) => {
              setRunId(e.target.value);
              reset();
            }}
            className="border-rule w-full max-w-md border bg-white px-3 py-2"
          >
            {runs.map((r) => (
              <option key={r.run_id} value={r.run_id}>
                {r.model_id}{r.is_reference ? "" : " (non référence)"} – {r.run_id}
              </option>
            ))}
          </select>
          {selected && !selected.is_reference && (
            <p className="bg-warn-bg text-warn mt-2 max-w-md px-3 py-2 text-sm">
              Cette exécution n&apos;est pas un résultat de référence (test de fumée, sous-échantillon ou dépôt modifié).
            </p>
          )}
        </div>

        <fieldset>
          <legend className="text-muted mb-2 text-sm">Image du jeu de test</legend>
          <div className="grid grid-cols-4 gap-2 sm:grid-cols-6">
            {gallery.items.map((it) => (
              <label key={it.id} className="relative block cursor-pointer">
                <input
                  type="radio"
                  name="image"
                  value={it.id}
                  checked={imageId === it.id}
                  onChange={() => {
                    setImageId(it.id);
                    reset();
                  }}
                  className="peer sr-only"
                />
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={`/api/gallery/${it.id}/image`}
                  alt={`Radiographie d'exemple ${it.id}`}
                  width={112}
                  height={112}
                  className="peer-checked:outline-est peer-focus-visible:outline-est aspect-square w-full object-cover outline outline-2 outline-transparent peer-checked:outline-4"
                />
              </label>
            ))}
          </div>
          <p className="text-muted mt-2 text-xs">{gallery.attribution}</p>
        </fieldset>

        <div className="flex flex-wrap gap-3">
          <button
            type="button"
            onClick={() => run("predict")}
            disabled={busy !== null || !runId || !imageId}
            className="bg-est px-4 py-2 font-medium text-white disabled:opacity-50"
          >
            {busy === "predict" ? "Calcul en cours…" : "Prédire"}
          </button>
          <button
            type="button"
            onClick={() => run("explain")}
            disabled={busy !== null || !runId || !imageId}
            className="border-est text-est border px-4 py-2 font-medium disabled:opacity-50"
          >
            {busy === "explain" ? "Calcul en cours…" : "Afficher la carte Grad-CAM"}
          </button>
        </div>
      </div>

      <div aria-live="polite" className="space-y-6">
        {error && (
          <p role="alert" className="bg-warn-bg text-warn max-w-[60ch] px-3 py-2">
            {error}
          </p>
        )}
        {pred && (
          <section>
            <h2 className="text-xl font-semibold">Prédiction</h2>
            <p className="mt-2 text-3xl tabular-nums">{num(pred.probability_pneumonia)}</p>
            <p className="text-muted text-sm">
              Probabilité de pneumonie estimée par la seed {pred.seed}.{" "}
              {pred.resized_from ? `Image redimensionnée depuis ${pred.resized_from} pixels. ` : ""}
            </p>
            <ul className="mt-3 space-y-1">
              {Object.entries(pred.operating_points).map(([name, op]) => (
                <li key={name}>
                  Au seuil {name.split("_")[0]} ({num(op.threshold)}) : le modèle prédit{" "}
                  <strong>{op.predicted_pneumonia ? "pneumonie" : "normal"}</strong>.
                </li>
              ))}
            </ul>
            <p className="mt-3">
              Étiquette du jeu de données : <strong>{LABEL[pred.ground_truth_label as 0 | 1]}</strong>.
            </p>
          </section>
        )}
        {expl && (
          <section>
            <h2 className="text-xl font-semibold">{expl.method}</h2>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={`data:image/png;base64,${expl.overlay_png_base64}`}
              alt="Radiographie avec la carte Grad-CAM superposée : les zones chaudes sont celles qui ont le plus contribué à la sortie du modèle"
              className="mt-2 w-full max-w-sm"
            />
            <p className="text-muted mt-2 max-w-[60ch] text-sm">{expl.note}</p>
          </section>
        )}
        {!pred && !expl && !error && (
          <p className="text-muted max-w-[60ch]">Choisissez une image puis lancez une prédiction.</p>
        )}
      </div>
    </div>
  );
}
