export function ReportProgress({ value, label }: { value: number; label: string }) {
  const normalized = Math.min(100, Math.max(0, value))
  return (
    <div><div className="mb-2 flex items-center justify-between text-sm"><strong>{label}</strong><span className="font-mono font-black">{normalized}%</span></div><div role="progressbar" aria-label={label} aria-valuemin={0} aria-valuemax={100} aria-valuenow={normalized} className="h-3 overflow-hidden rounded-full bg-slate-100"><div className="h-full rounded-full bg-[var(--accent)] transition-all" style={{ width: `${normalized}%` }} /></div></div>
  )
}
