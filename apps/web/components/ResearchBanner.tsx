export const DISCLAIMER = "Prototype de recherche. Ne pas utiliser pour un diagnostic ou une décision clinique.";

export function ResearchBanner() {
  return (
    <div role="note" className="bg-warn-bg text-warn border-b border-warn/30 px-4 py-2 text-sm font-medium">
      <p className="mx-auto max-w-6xl">{DISCLAIMER}</p>
    </div>
  );
}
