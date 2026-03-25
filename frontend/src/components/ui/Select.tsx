import { SelectHTMLAttributes, useId } from 'react'

interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label?: string
  options: { value: string; label: string }[]
}

export default function Select({ label, options, className = '', id, ...props }: SelectProps) {
  const generatedId = useId()
  const selectId = id ?? generatedId
  return (
    <div className="space-y-1">
      {label && <label htmlFor={selectId} className="block text-xs font-medium text-surface-300">{label}</label>}
      <select
        id={selectId}
        {...props}
        className={`w-full bg-surface-900 border border-surface-600 rounded-md px-3 py-2 text-sm text-surface-100 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent ${className}`}
      >
        {options.map((opt) => (
          <option key={opt.value} value={opt.value} className="bg-surface-800">
            {opt.label}
          </option>
        ))}
      </select>
    </div>
  )
}
