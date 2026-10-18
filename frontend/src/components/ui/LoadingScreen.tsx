export function LoadingScreen({ label = 'Đang tải dữ liệu' }: { label?: string }) {
  return (
    <div className="grid min-h-screen place-items-center bg-[var(--canvas)] px-6">
      <div className="text-center" role="status" aria-live="polite">
        <span className="mx-auto block size-10 animate-spin rounded-full border-2 border-slate-300 border-t-[var(--accent)]" />
        <p className="mt-4 text-sm font-semibold text-slate-600">{label}</p>
      </div>
    </div>
  )
}

