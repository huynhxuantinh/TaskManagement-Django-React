import { useId, type InputHTMLAttributes } from 'react'

interface FieldProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string
  error?: string
  hint?: string
}

export function Field({ label, error, hint, id, className = '', ...props }: FieldProps) {
  const generatedId = useId()
  const inputId = id ?? generatedId
  const descriptionId = `${inputId}-description`
  return (
    <label htmlFor={inputId} className="block">
      <span className="mb-2 block text-sm font-bold text-slate-800">{label}</span>
      <input
        id={inputId}
        aria-invalid={Boolean(error)}
        aria-describedby={error || hint ? descriptionId : undefined}
        className={`min-h-12 w-full rounded-xl border bg-white px-4 text-[15px] text-slate-950 outline-none transition placeholder:text-slate-400 focus:border-slate-700 focus:ring-2 focus:ring-[var(--accent-soft)] ${error ? 'border-red-400' : 'border-slate-300'} ${className}`}
        {...props}
      />
      {(error || hint) && (
        <span
          id={descriptionId}
          className={`mt-2 block text-sm ${error ? 'text-red-700' : 'text-slate-500'}`}
        >
          {error ?? hint}
        </span>
      )}
    </label>
  )
}

