import { useCallback, useMemo, useState, type ReactNode } from 'react'

import { ToastContext, type ToastTone } from './ToastContext'

interface ToastItem { id: number; message: string; tone: ToastTone }

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([])
  const notify = useCallback((message: string, tone: ToastItem['tone'] = 'success') => {
    const id = Date.now()
    setItems((current) => [...current, { id, message, tone }])
    window.setTimeout(() => setItems((current) => current.filter((item) => item.id !== id)), 3500)
  }, [])
  const value = useMemo(() => notify, [notify])
  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="fixed bottom-5 right-5 z-[60] grid max-w-sm gap-2" aria-live="polite">
        {items.map((item) => (
          <div key={item.id} className={`rounded-xl px-4 py-3 text-sm font-bold text-white shadow-xl ${item.tone === 'success' ? 'bg-emerald-700' : 'bg-red-700'}`}>
            {item.message}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}

