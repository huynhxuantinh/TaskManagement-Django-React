import { useEffect, useRef, type ReactNode } from 'react'

export function Modal({
  open,
  title,
  children,
  onClose,
}: {
  open: boolean
  title: string
  children: ReactNode
  onClose: () => void
}) {
  const modalRef = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (open) modalRef.current?.focus()
  }, [open])
  if (!open) return null
  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-slate-950/55 p-4" onMouseDown={onClose}>
      <div
        ref={modalRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
        tabIndex={-1}
        onKeyDown={(event) => event.key === 'Escape' && onClose()}
        onMouseDown={(event) => event.stopPropagation()}
        className="w-full max-w-xl rounded-2xl bg-white p-6 shadow-2xl outline-none"
      >
        <h2 id="modal-title" className="text-xl font-extrabold text-slate-950">
          {title}
        </h2>
        <div className="mt-5">{children}</div>
      </div>
    </div>
  )
}

