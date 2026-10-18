import { Route, Routes } from 'react-router-dom'

function HomePage() {
  return (
    <main className="mx-auto flex min-h-screen max-w-5xl items-center px-6 py-16">
      <section className="w-full rounded-3xl border border-slate-200 bg-white p-10 shadow-xl shadow-slate-200/50">
        <p className="mb-4 text-sm font-semibold uppercase tracking-[0.2em] text-blue-600">
          Internal workspace
        </p>
        <h1 className="text-4xl font-bold tracking-tight text-slate-950">
          Task Management
        </h1>
        <p className="mt-4 max-w-2xl text-lg leading-8 text-slate-600">
          Nền tảng giao việc và theo dõi tiến độ dự án nội bộ.
        </p>
        <div className="mt-8 flex flex-wrap gap-3" aria-label="Trạng thái hệ thống">
          <span className="rounded-full bg-emerald-50 px-4 py-2 text-sm font-medium text-emerald-700">
            Django API sẵn sàng
          </span>
          <span className="rounded-full bg-blue-50 px-4 py-2 text-sm font-medium text-blue-700">
            React 19
          </span>
          <span className="rounded-full bg-violet-50 px-4 py-2 text-sm font-medium text-violet-700">
            PostgreSQL 18
          </span>
        </div>
      </section>
    </main>
  )
}

export default function App() {
  return (
    <Routes>
      <Route path="*" element={<HomePage />} />
    </Routes>
  )
}
