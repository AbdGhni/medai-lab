import type { ReliabilityPoint } from "@/lib/api";
import { num } from "@/lib/format";

interface Props {
  label: string;
  points: ReliabilityPoint[];
}

/** Diagramme de fiabilité : probabilité prédite (x) contre fréquence observée (y). Diagonale = calibration parfaite. */
export function ReliabilityPlot({ label, points }: Props) {
  const S = 180;
  const pad = 22;
  const sc = (v: number) => pad + v * (S - 2 * pad);
  const sy = (v: number) => S - pad - v * (S - 2 * pad);
  const desc = points.length
    ? points.map((p) => `prédit ${num(p.mean_prob, 2)} observé ${num(p.observed_freq, 2)} (n=${p.n})`).join(" ; ")
    : "aucune donnée";
  return (
    <svg role="img" aria-label={`${label} : ${desc}`} viewBox={`0 0 ${S} ${S}`} className="h-auto w-full max-w-[200px]">
      <rect x={pad} y={pad} width={S - 2 * pad} height={S - 2 * pad} fill="none" stroke="var(--color-rule)" />
      <line x1={sc(0)} y1={sy(0)} x2={sc(1)} y2={sy(1)} stroke="var(--color-muted)" strokeDasharray="3 3" />
      {points.length > 1 && (
        <polyline
          fill="none"
          stroke="var(--color-est)"
          strokeWidth={1.5}
          points={points.map((p) => `${sc(p.mean_prob)},${sy(p.observed_freq)}`).join(" ")}
        />
      )}
      {points.map((p) => (
        <circle key={p.bin} cx={sc(p.mean_prob)} cy={sy(p.observed_freq)} r={2 + Math.min(4, Math.sqrt(p.n) / 6)} fill="var(--color-est)">
          <title>{`prédit ${num(p.mean_prob, 2)} ; observé ${num(p.observed_freq, 2)} ; n = ${p.n}`}</title>
        </circle>
      ))}
    </svg>
  );
}
