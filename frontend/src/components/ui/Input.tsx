import { InputHTMLAttributes, useId } from 'react'

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string
  error?: string
  hint?: string
}

export default function Input({ label, error, hint, className = '', id, ...props }: InputProps) {
  const generatedId = useId()
  const inputId = id ?? generatedId
  return (
    <div className="space-y-1">
      {label && <label htmlFor={inputId} className="block text-xs font-medium text-surface-300">{label}</label>}
      <input
        id={inputId}
        {...props}
        className={`w-full bg-surface-900 border ${error ? 'border-red-500' : 'border-surface-600'} rounded-md px-3 py-2 text-sm text-surface-100 placeholder-surface-400 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent transition ${className}`}
      />
      {hint && !error && <p className="text-xs text-surface-400">{hint}</p>}
      {error && <p className="text-xs text-red-400">{error}</p>}
    </div>
  )
}
