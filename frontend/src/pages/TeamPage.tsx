import { useState } from 'react'

import { useAuth } from '../auth/AuthContext'
import { StatePanel } from '../components/ui/StatePanel'
import { MembersPanel } from '../features/core/MembersPanel'
import { useAllPages } from '../hooks/useAllPages'
import type { Project } from '../types/api'

export function TeamPage() {
  const { user } = useAuth()
  const { data, loading, error } = useAllPages<Project>('/api/v1/projects/?page_size=100&ordering=name')
  const [selectedId, setSelectedId] = useState('')
  const effectiveId = selectedId || String(data?.results[0]?.id ?? '')
  const selected = data?.results.find((project) => String(project.id) === effectiveId)

  if (error) return <StatePanel eyebrow="Đội ngũ" title="Không tải được dữ liệu" description={error} />
  return (
    <div className="space-y-6">
      <header><p className="section-kicker">Danh bạ thành viên</p><h2 className="mt-1 text-3xl font-black tracking-tight">Đội ngũ theo dự án</h2><p className="mt-2 text-sm text-slate-600">Quyền truy cập và danh sách thành viên luôn bám theo từng dự án.</p></header>
      {loading && <div className="h-28 animate-pulse rounded-2xl bg-white" />}
      {!loading && data?.results.length === 0 && <StatePanel eyebrow="Đội ngũ" title="Chưa có đội dự án" description="Bạn chưa thuộc dự án nào trong hệ thống." />}
      {data && data.results.length > 0 && (
        <label className="block max-w-xl rounded-2xl border border-slate-200 bg-white p-4"><span className="mb-2 block text-sm font-bold">Chọn dự án</span><select value={effectiveId} onChange={(event) => setSelectedId(event.target.value)} className="min-h-12 w-full rounded-xl border border-slate-300 bg-white px-4 text-sm font-semibold outline-none focus:border-slate-700 focus:ring-2 focus:ring-[var(--accent-soft)]">{data.results.map((project) => <option key={project.id} value={project.id}>{project.name} · {project.member_count} thành viên</option>)}</select></label>
      )}
      {selected && user && <MembersPanel project={selected} user={user} />}
    </div>
  )
}
