import { interval } from "@/lib/format";

interface Props {
  label: string;
  mean: number | null;
  low: number | null;
  high: number | null;
  min?: number;
  max?: number;
  /** Repère vertical optionnel (ex. 0,5 = hasard pour l'AUC). */
  reference?: { value: number; label: string };
}

/**
 * Intervalle de confiance sur un axe commun : le point est l'estimation, la barre l'intervalle.
 * Sans estimation, aucune forme n'est dessinée.
 */
export function IntervalBar({ label, mean, low, high, min = 0.5, max = 1, reference }: Props) {
  const W = 320;
  const H = 22;
  const pad = 6;
  const x = (v: number) => pad + ((Math.min(Math.max(v, min), max) - min) / (max - min)) * (W - 2 * pad);
  const text = interval(mean, low, high);
  const hasEstimate = mean !== null;
  return (
    <svg
      role="img"
      aria-label={`${label} : ${text}`}
      viewBox={`0 0 ${W} ${H}`}
      className="h-[22px] w-full max-w-[320px]"
    >
      <line x1={pad} x2={W - pad} y1={H / 2} y2={H / 2} stroke="var(--color-rule)" strokeWidth={1} />
      {reference && (
        <line
          x1={x(reference.value)}
          x2={x(reference.value)}
          y1={3}
          y2={H - 3}
          stroke="var(--color-muted)"
          strokeWidth={1}
          strokeDasharray="2 2"
        >
          <title>{reference.label}</title>
        </line>
      )}
      {hasEstimate && low !== null && high !== null && (
        <>
          <line x1={x(low)} x2={x(high)} y1={H / 2} y2={H / 2} stroke="var(--color-est-soft)" strokeWidth={5} strokeLinecap="butt" />
          <line x1={x(low)} x2={x(low)} y1={5} y2={H - 5} stroke="var(--color-est)" strokeWidth={1.5} />
          <line x1={x(high)} x2={x(high)} y1={5} y2={H - 5} stroke="var(--color-est)" strokeWidth={1.5} />
        </>
      )}
      {hasEstimate && mean !== null && <circle cx={x(mean)} cy={H / 2} r={4} fill="var(--color-est)" />}
    </svg>
  );
}
