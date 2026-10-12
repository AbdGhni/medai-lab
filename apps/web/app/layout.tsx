import type { Metadata } from "next";
import type { ReactNode } from "react";
import "./globals.css";
import { Nav } from "@/components/Nav";
import { ResearchBanner } from "@/components/ResearchBanner";

export const metadata: Metadata = {
  title: "MedAI Lab",
  description:
    "Évaluation reproductible de modèles d'IA pour l'imagerie médicale. Prototype de recherche, aucun usage clinique.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="fr">
      <body className="min-h-screen">
        <ResearchBanner />
        <Nav />
        <main className="mx-auto max-w-6xl px-4 py-10">{children}</main>
        <footer className="border-t border-rule">
          <p className="text-muted mx-auto max-w-6xl px-4 py-6 text-sm">
            Code et protocole d&apos;évaluation :{" "}
            <a className="underline underline-offset-4" href="https://github.com/AbdGhni/medai-lab">
              github.com/AbdGhni/medai-lab
            </a>
            . Aucune image n&apos;est envoyée, stockée ni journalisée.
          </p>
        </footer>
      </body>
    </html>
  );
}
