import { Outlet } from 'react-router-dom'

export function AuthLayout() {
  return (
    <main className="auth-grid min-h-screen bg-[var(--ink)]">
      <section className="relative hidden overflow-hidden p-10 text-white lg:flex lg:flex-col lg:justify-between">
        <div className="auth-orbit auth-orbit-one" />
        <div className="auth-orbit auth-orbit-two" />
        <div className="relative z-10 flex items-center gap-3">
          <span className="grid size-11 place-items-center rounded-xl bg-[var(--accent)] font-mono text-sm font-black text-slate-950">TM</span>
          <div>
            <strong className="block">Task Management</strong>
            <span className="font-mono text-[10px] uppercase tracking-[0.2em] text-slate-400">Internal Operations</span>
          </div>
        </div>
        <div className="relative z-10 max-w-xl pb-10">
          <p className="font-mono text-xs font-bold uppercase tracking-[0.22em] text-[var(--accent)]">Project clarity / team velocity</p>
          <h1 className="mt-5 text-5xl font-black leading-[1.03] tracking-[-0.045em]">Biến tiến độ thành tín hiệu rõ ràng.</h1>
          <p className="mt-6 max-w-lg text-lg leading-8 text-slate-300">Một workspace tập trung để giao việc, nhận diện điểm nghẽn và giữ cả đội cùng một nhịp.</p>
          <div className="mt-10 grid grid-cols-3 gap-px overflow-hidden rounded-2xl bg-white/10">
            {['Dự án', 'Công việc', 'Báo cáo'].map((item, index) => (
              <div key={item} className="bg-white/5 p-4 backdrop-blur">
                <span className="font-mono text-xs text-[var(--accent)]">0{index + 1}</span>
                <strong className="mt-2 block text-sm">{item}</strong>
              </div>
            ))}
          </div>
        </div>
      </section>
      <section className="grid min-h-screen place-items-center bg-[var(--canvas)] px-5 py-10 sm:px-10">
        <div className="w-full max-w-md"><Outlet /></div>
      </section>
    </main>
  )
}

