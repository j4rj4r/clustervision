interface BadgeProps {
  variant?: 'default' | 'success' | 'warning' | 'danger' | 'info'
  children: React.ReactNode
}

const variants: Record<string, string> = {
  default: 'bg-slate-700 text-slate-300',
  success: 'bg-emerald-900/50 text-emerald-400 ring-1 ring-emerald-500/30',
  warning: 'bg-amber-900/50 text-amber-400 ring-1 ring-amber-500/30',
  danger: 'bg-red-900/50 text-red-400 ring-1 ring-red-500/30',
  info: 'bg-brand-900/50 text-brand-400 ring-1 ring-brand-500/30',
}

export default function Badge({ variant = 'default', children }: BadgeProps) {
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${variants[variant]}`}>
      {children}
    </span>
  )
}
