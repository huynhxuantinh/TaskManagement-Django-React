import type { ReactNode } from 'react'

export function StatePanel({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow?: string
  title: string
  description: string
  action?: ReactNode
}) {
  return (
    <section className="max-w-lg border-l-4 border-[var(--accent)] bg-white p-7 shadow-[var(--shadow)]">
      {eyebrow && (
        <p className="font-mono text-xs font-bold uppercase tracking-[0.18em] text-[var(--ink-soft)]">
          {eyebrow}
        </p>
      )}
      <h1 className="mt-2 text-2xl font-extrabold tracking-tight text-[var(--ink)]">{title}</h1>
      <p className="mt-3 leading-7 text-slate-600">{description}</p>
      {action && <div className="mt-6">{action}</div>}
    </section>
  )
}

