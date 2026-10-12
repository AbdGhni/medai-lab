from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.settings import Settings

from .conftest import decode_png

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def _run_id(client: TestClient) -> str:
    return str(client.get("/evaluations").json()["items"][0]["run_id"])


def test_health_has_disclaimer_and_research_header(client: TestClient) -> None:
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert "Ne pas utiliser pour un diagnostic" in body["disclaimer"]
    assert body["n_reports"] == 1 and body["n_gallery_images"] == 6
    assert r.headers["X-Research-Use-Only"] == "true"


def test_every_json_endpoint_carries_disclaimer(client: TestClient) -> None:
    rid = _run_id(client)
    for path in ("/health", "/models", "/evaluations", f"/evaluations/{rid}", "/gallery"):
        assert "disclaimer" in client.get(path).json(), path
    body = {"run_id": rid, "image_id": "t000"}
    assert "disclaimer" in client.post("/predict", json=body).json()
    assert "disclaimer" in client.post("/explain", json=body).json()


def test_no_report_means_no_evaluation_not_a_default_value(empty_client: TestClient) -> None:
    assert empty_client.get("/evaluations").json()["items"] == []
    assert empty_client.get("/models").json()["items"] == []
    r = empty_client.get("/evaluations/inconnu")
    assert r.status_code == 404 and "Aucune évaluation disponible" in r.json()["detail"]


def test_displayed_metrics_equal_report_file(
    client: TestClient, workspace: dict[str, Path]
) -> None:
    rid = _run_id(client)
    file_report = json.loads((workspace["run"] / "report.json").read_text(encoding="utf-8"))
    api = client.get(f"/evaluations/{rid}").json()
    assert api["report"]["aggregate"] == file_report["aggregate"]
    s = api["summary"]
    assert s["auc"]["mean"] == file_report["aggregate"]["auc"]["mean"]
    # un rapport 28x28 sur données synthétiques n'est jamais présenté comme référence
    assert s["is_reference"] is False and s["size"] == 28


def test_invalid_report_is_not_served(workspace: dict[str, Path], tmp_path: Path) -> None:
    reports = tmp_path / "reports"
    shutil.copytree(workspace["reports"], reports)
    run = next(reports.iterdir())
    data = json.loads((run / "report.json").read_text(encoding="utf-8"))
    data["provenance"]["commit"] = "inconnu"  # provenance incomplète
    (run / "report.json").write_text(json.dumps(data), encoding="utf-8")
    c = TestClient(
        create_app(
            Settings(reports_dir=reports, artifacts_dir=tmp_path, gallery_dir=workspace["gallery"])
        )
    )
    assert c.get("/evaluations").json()["items"] == []
    assert c.get("/health").json()["n_invalid_reports"] == 1
    assert c.get(f"/evaluations/{run.name}").status_code == 404


def test_path_traversal_is_rejected(client: TestClient) -> None:
    assert client.get("/evaluations/..%2F..%2Fetc%2Fpasswd").status_code == 404
    r = client.post("/predict", json={"run_id": "../x", "image_id": "t000"})
    assert r.status_code == 422
    r = client.post("/predict", json={"run_id": _run_id(client), "image_id": "../../etc/passwd"})
    assert r.status_code == 422
    assert client.get("/gallery/..%2Fmanifest/image").status_code == 404


def test_gallery_lists_labels_and_serves_png(client: TestClient) -> None:
    g = client.get("/gallery").json()
    assert g["license"] == "synthetic"  # licence du bundle de test
    assert "CC BY 4.0" in g["attribution"] and "Kermany" in g["attribution"]
    assert {i["label_name"] for i in g["items"]} == {"normal", "pneumonie"}
    img = client.get("/gallery/t000/image")
    assert img.status_code == 200 and img.content.startswith(PNG_MAGIC)
    assert client.get("/gallery/zzz/image").status_code == 404


def test_predict_returns_probability_and_thresholds(client: TestClient) -> None:
    r = client.post("/predict", json={"run_id": _run_id(client), "image_id": "t000"})
    assert r.status_code == 200
    body = r.json()
    assert 0.0 <= body["probability_pneumonia"] <= 1.0
    assert set(body["operating_points"]) == {"S1_youden", "S2_sens95"}
    for op in body["operating_points"].values():
        assert op["predicted_pneumonia"] == (body["probability_pneumonia"] >= op["threshold"])
    assert body["ground_truth_label"] in (0, 1)
    assert "Pas un avis médical" in body["note"]


def test_explain_returns_valid_pngs_and_flags_missing_sanity_check(client: TestClient) -> None:
    r = client.post("/explain", json={"run_id": _run_id(client), "image_id": "t001"})
    assert r.status_code == 200
    body = r.json()
    assert decode_png(body["overlay_png_base64"]).startswith(PNG_MAGIC)
    assert decode_png(body["heatmap_png_base64"]).startswith(PNG_MAGIC)
    assert body["sanity_checked"] is False and "indice de localisation" in body["note"].lower()


def test_unknown_image_and_run(client: TestClient) -> None:
    assert (
        client.post("/predict", json={"run_id": _run_id(client), "image_id": "t999"}).status_code
        == 404
    )
    assert client.post("/predict", json={"run_id": "nope", "image_id": "t000"}).status_code == 404


def test_missing_weights_gives_409_not_a_fake_prediction(
    workspace: dict[str, Path], tmp_path: Path
) -> None:
    s = Settings(
        reports_dir=workspace["reports"],
        artifacts_dir=tmp_path / "vide",
        gallery_dir=workspace["gallery"],
    )
    c = TestClient(create_app(s))
    rid = _run_id(c)
    assert c.post("/predict", json={"run_id": rid, "image_id": "t000"}).status_code == 409
    assert c.post("/explain", json={"run_id": rid, "image_id": "t000"}).status_code == 409


def test_uploads_are_refused_and_nothing_is_written(
    client: TestClient, workspace: dict[str, Path]
) -> None:
    def snapshot() -> set[str]:
        return {str(p) for p in workspace["root"].rglob("*")}

    before = snapshot()
    rid = _run_id(client)
    png = (workspace["gallery"] / "t000.png").read_bytes()
    # image en base64 dans le JSON : champ inconnu refusé
    r1 = client.post("/predict", json={"run_id": rid, "image_id": "t000", "image": "AAAA"})
    # multipart : refusé
    r2 = client.post("/predict", files={"file": ("x.png", png, "image/png")})
    # aucune route d'upload
    r3 = client.post("/upload", files={"file": ("x.png", png, "image/png")})
    r4 = client.put("/gallery/t000/image", content=png)
    assert r1.status_code == 422 and r2.status_code == 422
    # la réponse d'erreur n'écho pas le contenu reçu
    assert b"PNG" not in r2.content and "AAAA" not in r1.text
    assert r3.status_code == 404 and r4.status_code == 405
    assert snapshot() == before


def test_openapi_documents_research_only(client: TestClient) -> None:
    spec = client.get("/openapi.json").json()
    assert "Ne pas utiliser pour un diagnostic" in spec["info"]["description"]


# ------------------------------------------------------------------ analyses complémentaires


@pytest.fixture()
def analysed(workspace, bundle, tmp_path):  # type: ignore[no-untyped-def]
    """Copie du espace de travail avec une analyse de sanité et une de calibration."""
    import shutil

    from medai_ml import analyze
    from medai_ml.report import load_report

    ws = tmp_path / "ws"
    shutil.copytree(workspace["root"], ws)
    run_id = next((ws / "reports").iterdir()).name
    assert load_report(ws / "reports" / run_id / "report.json")
    analyze.calibrate_run(ws / "reports", run_id)
    analyze.sanity_run(ws / "reports", ws / "artifacts", run_id, n_per_class=2, bundle=bundle)
    s = Settings(
        reports_dir=ws / "reports", artifacts_dir=ws / "artifacts", gallery_dir=ws / "gallery"
    )
    return TestClient(create_app(s)), run_id, ws


def test_analyses_empty_for_report_without_analyses(client: TestClient) -> None:
    run_id = client.get("/evaluations").json()["items"][0]["run_id"]
    r = client.get(f"/evaluations/{run_id}/analyses")
    assert r.status_code == 200 and r.json()["items"] == []
    assert client.get(f"/evaluations/{run_id}/analyses/robustness").status_code == 404


def test_analyses_listed_and_served_with_disclaimer(analysed) -> None:  # type: ignore[no-untyped-def]
    c, run_id, _ = analysed
    names = {a["name"] for a in c.get(f"/evaluations/{run_id}/analyses").json()["items"]}
    assert names == {"calibration", "gradcam_sanity"}
    doc = c.get(f"/evaluations/{run_id}/analyses/calibration").json()
    assert doc["run_id"] == run_id and "Ne pas utiliser" in doc["disclaimer"]


def test_analysis_unknown_run_or_name_or_traversal(analysed) -> None:  # type: ignore[no-untyped-def]
    c, run_id, _ = analysed
    assert c.get("/evaluations/inconnu/analyses").status_code == 404
    assert c.get("/evaluations/inconnu/analyses/calibration").status_code == 404
    for bad in ("..%2Freport", "report", "../../etc/passwd", "calibration.json"):
        assert c.get(f"/evaluations/{run_id}/analyses/{bad}").status_code == 404


def test_inconsistent_analysis_is_not_served(analysed) -> None:  # type: ignore[no-untyped-def]
    import json

    c, run_id, ws = analysed
    p = ws / "reports" / run_id / "analyses" / "calibration.json"
    doc = json.loads(p.read_text())
    doc["run_id"] = "autre"
    p.write_text(json.dumps(doc))
    assert c.get(f"/evaluations/{run_id}/analyses/calibration").status_code == 404


def test_explain_reports_sanity_once_executed(analysed) -> None:  # type: ignore[no-untyped-def]
    c, run_id, _ = analysed
    image_id = c.get("/gallery").json()["items"][0]["id"]
    body = c.post("/explain", json={"run_id": run_id, "image_id": image_id}).json()
    assert body["sanity_checked"] is True and isinstance(body["sanity_passed"], bool)
    assert "indice de localisation" in body["note"].lower()
