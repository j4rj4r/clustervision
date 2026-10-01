import { useEffect, useRef, useState } from 'react'
import { Check, ChevronDown, Server } from 'lucide-react'
import { useClusters } from '../../hooks/useCluster'
import { useClusterStore } from '../../store/clusterStore'
import Badge from '../ui/Badge'

export default function ClusterSwitcher() {
  const { data: clusters = [] } = useClusters()
  const { activeCluster, setActiveCluster } = useClusterStore()
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    const handleClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    const handleKey = (e: KeyboardEvent) => { if (e.key === 'Escape') setOpen(false) }
    document.addEventListener('mousedown', handleClick)
    document.addEventListener('keydown', handleKey)
    return () => {
      document.removeEventListener('mousedown', handleClick)
      document.removeEventListener('keydown', handleKey)
    }
  }, [open])

  if (clusters.length <= 1) {
    return (
      <div className="flex items-center gap-1.5">
        <Server size={13} className="text-surface-300 shrink-0" />
        <span className="text-xs text-surface-200 font-mono">{activeCluster}</span>
      </div>
    )
  }

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen((o) => !o)}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-label="Active cluster"
        className="flex items-center gap-1.5 text-xs text-surface-200 font-mono hover:text-white transition-colors"
      >
        <Server size={13} className="text-surface-300 shrink-0" />
        {activeCluster}
        <ChevronDown size={13} className={`text-surface-400 transition-transform duration-150 ${open ? 'rotate-180' : ''}`} />
      </button>

      {open && (
        <div
          role="listbox"
          aria-label="Clusters"
          className="absolute left-0 top-full mt-2 w-56 bg-surface-800 border border-surface-600 rounded-lg shadow-2xl overflow-hidden z-50 py-1"
        >
          {clusters.map((c) => {
            const isActive = c.name === activeCluster
            return (
              <button
                key={c.name}
                role="option"
                aria-selected={isActive}
                onClick={() => { setActiveCluster(c.name); setOpen(false) }}
                className={`w-full flex items-center gap-2 px-3 py-2 text-left text-xs transition-colors ${
                  isActive ? 'bg-brand-600/10 text-brand-300' : 'text-surface-200 hover:bg-surface-700'
                }`}
              >
                <Server size={13} className={`shrink-0 ${isActive ? 'text-brand-400' : 'text-surface-400'}`} />
                <span className="font-mono truncate flex-1">{c.name}</span>
                {c.is_local && <Badge variant="success">local</Badge>}
                {isActive && <Check size={13} className="text-brand-400 shrink-0" />}
              </button>
            )
          })}
        </div>
      )}
    </div>
  )
}
