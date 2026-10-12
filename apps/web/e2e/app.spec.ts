import { expect, test } from "@playwright/test";

const WITH_REPORT = "http://127.0.0.1:3100";
const WITHOUT_REPORT = "http://127.0.0.1:3101";
const INTERVAL = /\d,\d{3} \[\d,\d{3} ; \d,\d{3}\]/;

test("sans rapport, aucune performance n'est affichée", async ({ page }) => {
  await page.goto(WITHOUT_REPORT + "/");
  await expect(page.getByRole("heading", { name: "Aucune évaluation disponible" })).toBeVisible();
  const text = (await page.locator("main").innerText()).replace(/\s+/g, " ");
  expect(text).not.toMatch(INTERVAL);
  expect(text).not.toMatch(/AUC\s*:?\s*\d/);
  await expect(page.locator("svg[role=img]")).toHaveCount(0);
});

test("une évaluation inconnue renvoie une page introuvable, pas des chiffres", async ({ page }) => {
  const res = await page.goto(WITH_REPORT + "/evaluations/inconnue");
  expect(res?.status()).toBe(404);
  await expect(page.locator("body")).not.toContainText(INTERVAL);
});

test("l'avertissement de recherche est présent sur chaque page", async ({ page }) => {
  for (const path of ["/", "/demo", "/limites"]) {
    await page.goto(WITH_REPORT + path);
    await expect(page.getByRole("note").first()).toContainText("Ne pas utiliser pour un diagnostic");
  }
});

test("un rapport synthétique 28×28 n'est jamais présenté comme référence", async ({ page }) => {
  await page.goto(WITH_REPORT + "/");
  await expect(page.getByRole("heading", { name: "Autres exécutions" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Résultats de référence" })).toHaveCount(0);
  await page.getByRole("link", { name: "simple_cnn" }).first().click();
  await expect(page.getByText("n'est pas un résultat de référence")).toBeVisible();
  const main = (await page.locator("main").innerText()).replace(/\s+/g, " ");
  expect(main).toMatch(INTERVAL);
  await expect(page.getByRole("heading", { name: /Seuil S1/ })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Provenance" })).toBeVisible();
});

test("les chiffres affichés sont ceux du rapport servi par l'API", async ({ page, request }) => {
  const list = await (await request.get("http://127.0.0.1:8100/evaluations")).json();
  const run = list.items[0];
  const detail = await (await request.get(`http://127.0.0.1:8100/evaluations/${run.run_id}`)).json();
  const auc = detail.report.aggregate.auc;
  const fr = (v: number) => v.toLocaleString("fr-FR", { minimumFractionDigits: 3, maximumFractionDigits: 3 });
  await page.goto(`${WITH_REPORT}/evaluations/${run.run_id}`);
  await expect(page.locator("main")).toContainText(`${fr(auc.mean)} [${fr(auc.ci_low)} ; ${fr(auc.ci_high)}]`);
});

test("démonstration : prédiction puis Grad-CAM sur une image d'exemple", async ({ page }) => {
  await page.goto(WITH_REPORT + "/demo");
  await expect(page.getByRole("button", { name: "Prédire" })).toBeEnabled();
  await page.getByRole("button", { name: "Prédire" }).click();
  await expect(page.getByRole("heading", { name: "Prédiction" })).toBeVisible();
  await expect(page.getByText(/Étiquette du jeu de données/)).toBeVisible();
  await page.getByRole("button", { name: "Afficher la carte Grad-CAM" }).click();
  await expect(page.getByRole("heading", { name: /Grad-CAM/ }).first()).toBeVisible();
  await expect(page.locator("img[src^='data:image/png;base64,']")).toBeVisible();
  await expect(page.getByText(/test de sanité/)).toBeVisible();
});

test("la page des limites expose les problèmes connus des données", async ({ page }) => {
  await page.goto(WITH_REPORT + "/limites");
  await expect(page.locator("main")).toContainText("doublons confirmés");
  await expect(page.locator("main")).toContainText("62,5 %");
});

async function runWithAnalyses(request: import("@playwright/test").APIRequestContext) {
  const list = await (await request.get("http://127.0.0.1:8100/evaluations")).json();
  for (const run of list.items) {
    const a = await (await request.get(`http://127.0.0.1:8100/evaluations/${run.run_id}/analyses`)).json();
    if (a.items.length > 0) return { run, analyses: a.items.map((i: { name: string }) => i.name) as string[] };
  }
  throw new Error("aucune évaluation avec analyses dans la fixture");
}

test("les analyses affichées sont celles de l'API, et seulement celles-là", async ({ page, request }) => {
  const { run } = await runWithAnalyses(request);
  const comp = await (await request.get(`http://127.0.0.1:8100/evaluations/${run.run_id}/analyses/comparison`)).json();
  await page.goto(`${WITH_REPORT}/evaluations/${run.run_id}/analyses`);
  await expect(page.getByRole("heading", { name: "Analyses complémentaires" })).toBeVisible();
  for (const h of ["Comparaison avec le modèle de référence", "Calibration", "Robustesse aux perturbations", "Test de sanité de Grad-CAM"]) {
    await expect(page.getByRole("heading", { name: h })).toBeVisible();
  }
  await expect(page.locator("main")).toContainText(comp.comparisons[0].wording);
  await expect(page.locator("main")).toContainText("Compression JPEG");
  await expect(page.locator("svg[role=img]").first()).toBeVisible();
  await expect(page.getByText("n'est pas un résultat de référence")).toBeVisible();
});

test("une évaluation sans analyses l'indique et n'affiche aucun chiffre", async ({ page, request }) => {
  const list = await (await request.get("http://127.0.0.1:8100/evaluations")).json();
  let target: string | null = null;
  for (const run of list.items) {
    const a = await (await request.get(`http://127.0.0.1:8100/evaluations/${run.run_id}/analyses`)).json();
    if (a.items.length === 0) target = run.run_id;
  }
  expect(target).not.toBeNull();
  await page.goto(`${WITH_REPORT}/evaluations/${target}/analyses`);
  await expect(page.getByText("Aucune valeur n'est affichée.")).toHaveCount(4);
  const text = (await page.locator("main").innerText()).replace(/\s+/g, " ");
  expect(text).not.toMatch(INTERVAL);
  await expect(page.locator("svg[role=img]")).toHaveCount(0);
});

test("la page d'analyses d'un identifiant inconnu est introuvable", async ({ page }) => {
  const res = await page.goto(WITH_REPORT + "/evaluations/inconnue/analyses");
  expect(res?.status()).toBe(404);
});

test("la démo indique que le test de sanité a été exécuté quand c'est le cas", async ({ page, request }) => {
  const { run, analyses } = await runWithAnalyses(request);
  expect(analyses).toContain("gradcam_sanity");
  const image = (await (await request.get("http://127.0.0.1:8100/gallery")).json()).items[0].id;
  const body = await (await request.post("http://127.0.0.1:8100/explain", { data: { run_id: run.run_id, image_id: image } })).json();
  expect(body.sanity_checked).toBe(true);
});
