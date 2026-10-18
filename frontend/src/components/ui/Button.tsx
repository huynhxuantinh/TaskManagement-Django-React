import type { ButtonHTMLAttributes } from 'react'

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: 'primary' | 'secondary' | 'ghost'
}

export function Button({ className = '', variant = 'primary', ...props }: ButtonProps) {
  const styles = {
    primary: 'bg-[var(--ink)] text-white hover:bg-slate-800 focus-visible:ring-[var(--accent)]',
    secondary: 'border border-slate-300 bg-white text-slate-800 hover:border-slate-500',
    ghost: 'text-slate-600 hover:bg-slate-100 hover:text-slate-950',
  }
  return (
    <button
      className={`inline-flex min-h-11 items-center justify-center gap-2 rounded-xl px-4 text-sm font-bold transition focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-55 ${styles[variant]} ${className}`}
      {...props}
    />
  )
}

