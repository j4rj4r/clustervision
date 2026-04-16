interface BadgeProps {
  variant?: 'default' | 'success' | 'warning' | 'danger' | 'info'
  dot?: boolean
  children: React.ReactNode
}

const variants: Record<string, string> = {
  default: 'bg-surface-700 text-surface-300 ring-1 ring-surface-500',
  success: 'bg-emerald-950/70 text-emerald-300 ring-1 ring-emerald-500/40',
  warning: 'bg-amber-950/70 text-amber-300 ring-1 ring-amber-500/40',
  danger:  'bg-red-950/70 text-red-300 ring-1 ring-red-500/40',
  info:    'bg-brand-900/60 text-brand-300 ring-1 ring-brand-500/40',
}

const dotColors: Record<string, string> = {
  default: 'bg-surface-400',
  success: 'bg-emerald-400',
  warning: 'bg-amber-400',
  danger:  'bg-red-400',
  info:    'bg-brand-400',
}

export default function Badge({ variant = 'default', dot, children }: BadgeProps) {
  return (
    <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-medium ${variants[variant]}`}>
      {dot && <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${dotColors[variant]}`} />}
      {children}
    </span>
  )
}
