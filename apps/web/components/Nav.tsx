import Link from "next/link";

const links = [
  { href: "/", label: "Évaluations" },
  { href: "/demo", label: "Essayer sur des images d'exemple" },
  { href: "/limites", label: "Données et limites" },
];

export function Nav() {
  return (
    <header className="border-b border-rule">
      <div className="mx-auto flex max-w-6xl flex-wrap items-baseline gap-x-8 gap-y-2 px-4 py-4">
        <Link href="/" className="text-lg font-semibold tracking-tight">
          MedAI Lab
        </Link>
        <nav aria-label="Navigation principale" className="flex flex-wrap gap-x-6 gap-y-1 text-sm">
          {links.map((l) => (
            <Link key={l.href} href={l.href} className="text-muted underline-offset-4 hover:text-ink hover:underline">
              {l.label}
            </Link>
          ))}
        </nav>
      </div>
    </header>
  );
}
