import { DemoClient } from "./DemoClient";

export const metadata = { title: "Essayer sur des images d'exemple | MedAI Lab" };

export default function DemoPage() {
  return (
    <div className="space-y-8">
      <section className="max-w-[68ch]">
        <h1 className="text-3xl font-semibold tracking-tight">Essayer sur des images d&apos;exemple</h1>
        <p className="mt-4">
          Choisissez une radiographie du jeu de test, puis lancez une prédiction ou une carte Grad-CAM. Seules ces images
          sont acceptées : vous ne pouvez pas en envoyer. Le résultat est celui d&apos;un modèle de recherche, pas un avis
          médical.
        </p>
      </section>
      <DemoClient />
    </div>
  );
}
