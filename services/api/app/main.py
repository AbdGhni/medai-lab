"""API MedAI Lab (recherche uniquement).

Principes : (1) toute performance affichée provient d'un rapport valide ; (2) l'inférence en
direct ne porte que sur les images de la galerie ; (3) aucune image n'est reçue, stockée ni
journalisée.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from medai_ml import DISCLAIMER, __version__

from .inference import Gallery, InferenceUnavailable, Predictor
from .schemas import (
    AnalysisEntry,
    AnalysisList,
    EvaluationDetail,
    EvaluationList,
    Explanation,
    GalleryItem,
    Health,
    ModelEntry,
    ModelList,
    Prediction,
    PredictRequest,
)
from .schemas import (
    Gallery as GallerySchema,
)
from .settings import Settings
from .store import ReportStore, summarize


def create_app(settings: Settings | None = None) -> FastAPI:
    cfg = settings or Settings()
    store = ReportStore(cfg.reports_dir)
    gallery = Gallery(cfg.gallery_dir)
    predictor = Predictor(cfg.artifacts_dir)

    app = FastAPI(
        title="MedAI Lab API",
        version=__version__,
        description=DISCLAIMER,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cfg.cors_origins,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        # Ne jamais renvoyer le contenu reçu (peut être binaire ou sensible) : on décrit seulement l'erreur.
        errors = [{"loc": list(e["loc"]), "msg": e["msg"], "type": e["type"]} for e in exc.errors()]
        return JSONResponse(status_code=422, content={"detail": errors, "disclaimer": DISCLAIMER})

    @app.middleware("http")
    async def research_header(request: Request, call_next: Any) -> Response:
        response: Response = await call_next(request)
        response.headers["X-Research-Use-Only"] = "true"
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/health", response_model=Health)
    def health() -> Health:
        return Health(
            status="ok",
            version=__version__,
            n_reports=len(store.all()),
            n_invalid_reports=len(store.invalid),
            n_gallery_images=len(gallery.items),
        )

    @app.get("/models", response_model=ModelList)
    def models() -> ModelList:
        by_model: dict[str, list[str]] = {}
        for rep in store.all():  # du plus récent au plus ancien
            by_model.setdefault(rep.model_id, []).append(rep.run_id)
        return ModelList(
            items=[
                ModelEntry(model_id=m, n_runs=len(r), latest_run_id=r[0])
                for m, r in by_model.items()
            ]
        )

    @app.get("/evaluations", response_model=EvaluationList)
    def evaluations() -> EvaluationList:
        return EvaluationList(items=[summarize(r) for r in store.all()])

    @app.get("/evaluations/{run_id}", response_model=EvaluationDetail)
    def evaluation(run_id: str) -> EvaluationDetail:
        rep = _get_report(run_id)
        return EvaluationDetail(report=rep.model_dump(mode="json"), summary=summarize(rep))

    @app.get("/evaluations/{run_id}/analyses", response_model=AnalysisList)
    def analyses(run_id: str) -> AnalysisList:
        _get_report(run_id)
        return AnalysisList(items=[AnalysisEntry(**a) for a in store.analyses(run_id)])

    @app.get("/evaluations/{run_id}/analyses/{name}")
    def analysis(run_id: str, name: str) -> dict[str, Any]:
        _get_report(run_id)
        doc = store.analysis(run_id, name)
        if doc is None:
            raise HTTPException(404, "Analyse non disponible pour cette évaluation.")
        return doc

    @app.get("/gallery", response_model=GallerySchema)
    def gallery_list() -> GallerySchema:
        names: dict[str, str] = gallery.manifest.get("label_names", {})
        return GallerySchema(
            license=str(gallery.manifest.get("license", "")),
            attribution=str(gallery.manifest.get("attribution", "")),
            selection=str(gallery.manifest.get("selection", "")),
            items=[
                GalleryItem(
                    id=i.id, label=i.label, label_name=names.get(str(i.label), str(i.label))
                )
                for i in gallery.items.values()
            ],
        )

    @app.get("/gallery/{image_id}/image")
    def gallery_image(image_id: str) -> Response:
        item = gallery.items.get(image_id)
        if item is None:
            raise HTTPException(404, "Image inconnue.")
        return Response(content=item.path.read_bytes(), media_type="image/png")

    def _get_report(run_id: str) -> Any:
        rep = store.get(run_id)
        if rep is None:
            raise HTTPException(404, "Aucune évaluation disponible pour cet identifiant.")
        return rep

    def _prepare(req: PredictRequest) -> tuple[Any, Any]:
        rep = _get_report(req.run_id)
        if req.image_id not in gallery.items:
            raise HTTPException(
                404, "Image inconnue : seules les images de la galerie sont acceptées."
            )
        return rep, gallery.load_uint8(req.image_id)

    @app.post("/predict", response_model=Prediction)
    def predict(req: PredictRequest) -> Prediction:
        rep, img = _prepare(req)
        seed = cfg.reference_seed
        try:
            prob, resized_from = predictor.predict(rep, img, seed)
        except InferenceUnavailable as exc:
            raise HTTPException(409, f"Inférence en direct indisponible : {exc}") from exc
        seed_res = next((s for s in rep.seeds if s.seed == seed), None)
        ops: dict[str, dict[str, float | bool]] = {}
        if seed_res is not None:
            for name, op in seed_res.operating_points.items():
                ops[name] = {"threshold": op.threshold, "predicted_pneumonia": prob >= op.threshold}
        return Prediction(
            run_id=req.run_id,
            image_id=req.image_id,
            seed=seed,
            probability_pneumonia=prob,
            operating_points=ops,
            ground_truth_label=gallery.items[req.image_id].label,
            note="Sortie d'un modèle de recherche sur une image d'exemple. Pas un avis médical.",
            resized_from=resized_from,
        )

    @app.post("/explain", response_model=Explanation)
    def explain(req: PredictRequest) -> Explanation:
        rep, img = _prepare(req)
        seed = cfg.reference_seed
        try:
            prob, overlay, heat = predictor.explain(rep, img, seed)
        except InferenceUnavailable as exc:
            raise HTTPException(409, f"Explication indisponible : {exc}") from exc
        sanity = store.analysis(rep.run_id, "gradcam_sanity")
        sanity_passed = None if sanity is None else bool(sanity.get("passes_all_seeds"))
        if sanity is None:
            note = (
                "Indice de localisation uniquement. Le test de sanité par randomisation des poids "
                "n'a pas encore été exécuté pour ce modèle."
            )
        elif sanity_passed:
            note = (
                "Indice de localisation uniquement. Le test de sanité par randomisation des poids "
                "a été exécuté : les cartes changent quand les poids sont randomisés. Cela ne "
                "démontre pas leur pertinence clinique."
            )
        else:
            note = (
                "Indice de localisation uniquement. Le test de sanité par randomisation des poids "
                "a été exécuté et n'est pas réussi pour toutes les seeds : ces cartes ne sont pas "
                "fiables pour ce modèle."
            )
        return Explanation(
            run_id=req.run_id,
            image_id=req.image_id,
            seed=seed,
            method="Grad-CAM (classe pneumonie)",
            probability_pneumonia=prob,
            overlay_png_base64=overlay,
            heatmap_png_base64=heat,
            sanity_checked=sanity is not None,
            sanity_passed=sanity_passed,
            note=note,
        )

    return app


app = create_app()
