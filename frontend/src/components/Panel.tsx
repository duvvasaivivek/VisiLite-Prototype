import type { ReactNode } from "react";

export function Panel({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="rounded-xl border border-slate-700 bg-panel p-4 shadow-lg">
      <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-accent">{title}</h2>
      {children}
    </section>
  );
}
