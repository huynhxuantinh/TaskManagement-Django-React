import { EstimateNotice } from './EstimateNotice'

export function ReportProgress({ value, label, missingEstimateCount, unfinishedTaskCount }: { value: number; label: string; missingEstimateCount?: number; unfinishedTaskCount?: number }) {
  const normalized = Math.min(100, Math.max(0, value))
  return (
    <div><div className="mb-2 flex items-center justify-between text-sm"><strong>{label}</strong><span className="font-mono font-black">{normalized}%</span></div><div role="progressbar" aria-label={label} aria-valuemin={0} aria-valuemax={100} aria-valuenow={normalized} className="h-3 overflow-hidden rounded-full bg-slate-100"><div className="h-full rounded-full bg-[var(--accent)] transition-all" style={{ width: `${normalized}%` }} /></div>{missingEstimateCount !== undefined && <EstimateNotice count={missingEstimateCount} className="mt-3 text-xs leading-5 text-slate-200" />}{unfinishedTaskCount !== undefined && <><p className="mt-2 text-xs text-slate-200">Còn {unfinishedTaskCount} công việc chưa hoàn thành.{normalized === 100 && unfinishedTaskCount > 0 && ' Tiến độ có thể đã được làm tròn hoặc nhập 100% trước khi đóng công việc.'}</p><p className="mt-2 text-xs leading-5 text-slate-200">Tiến độ tính theo trọng số giờ của công việc con hoặc công việc không có con; số lượng công việc bao gồm cả cha và con.</p></>}</div>
  )
}
