"""Accès aux rapports d'évaluation. Seuls les rapports valides selon le schéma sont servis."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from medai_ml.report import EvaluationReport, load_report

from .schemas import EvaluationSummary, MetricInterval

log = logging.getLogger("medai.store")


class ReportStore:
    def __init__(self, reports_dir: Path) -> None:
        self.reports_dir = Path(reports_dir)
        self._reports: dict[str, EvaluationReport] = {}
        self.invalid: list[str] = []
        self.reload()

    def reload(self) -> None:
        self._reports.clear()
        self.invalid.clear()
        if not self.reports_dir.exists():
            return
        for path in sorted(self.reports_dir.glob("*/report.json")):
            try:
                rep = load_report(path)
            except (ValueError, json.JSONDecodeError, OSError) as exc:
                log.warning("Rapport ignoré (invalide) : %s (%s)", path, type(exc).__name__)
                self.invalid.append(path.parent.name)
                continue
            if rep.run_id != path.parent.name:
                self.invalid.append(path.parent.name)
                continue
            self._reports[rep.run_id] = rep

    def get(self, run_id: str) -> EvaluationReport | None:
        return self._reports.get(run_id)

    def all(self) -> list[EvaluationReport]:
        return sorted(self._reports.values(), key=lambda r: r.created_at, reverse=True)


def summarize(rep: EvaluationReport) -> EvaluationSummary:
    auc = rep.aggregate.get("auc")
    size = int(rep.config.get("size", 0))
    subset = rep.config.get("train_subset")
    return EvaluationSummary(
        run_id=rep.run_id,
        model_id=rep.model_id,
        created_at=rep.created_at,
        n_seeds=len(rep.seeds),
        size=size,
        auc=None
        if auc is None
        else MetricInterval(mean=auc.mean, ci_low=auc.ci_low, ci_high=auc.ci_high),
        is_reference=(size == 224 and subset is None and not rep.provenance.dirty),
        dirty=rep.provenance.dirty,
        train_subset=subset,
        commit=rep.provenance.commit,
    )
