import { Loader2 } from 'lucide-react'
import { ButtonHTMLAttributes } from 'react'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost'
  size?: 'sm' | 'md'
  loading?: boolean
}

const variants: Record<string, string> = {
  primary:   'bg-brand-600 hover:bg-brand-700 text-white border border-brand-600 hover:border-brand-700',
  secondary: 'bg-transparent hover:bg-surface-700 text-surface-200 border border-surface-500 hover:border-surface-400',
  danger:    'bg-red-600 hover:bg-red-700 text-white border border-red-600 hover:border-red-700',
  ghost:     'bg-transparent hover:bg-surface-700 text-surface-300 hover:text-surface-100 border border-transparent',
}

const sizes: Record<string, string> = {
  sm: 'px-3 py-1.5 text-xs gap-1.5',
  md: 'px-4 py-2 text-sm gap-2',
}

export default function Button({
  variant = 'primary',
  size = 'md',
  loading,
  disabled,
  children,
  className = '',
  ...props
}: ButtonProps) {
  return (
    <button
      {...props}
      disabled={disabled || loading}
      className={`inline-flex items-center rounded-md font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${variants[variant]} ${sizes[size]} ${className}`}
    >
      {loading && <Loader2 size={14} className="animate-spin" />}
      {children}
    </button>
  )
}
