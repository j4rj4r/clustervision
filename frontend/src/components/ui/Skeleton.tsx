interface SkeletonProps {
  className?: string
}

export default function Skeleton({ className = '' }: SkeletonProps) {
  return (
    <div className={`animate-shimmer rounded ${className}`} />
  )
}

export function SkeletonRow({ cols = 5 }: { cols?: number }) {
  const widths = ['w-32', 'w-20', 'w-24', 'w-16', 'w-28', 'w-12']
  return (
    <tr className="border-b border-surface-700">
      <td className="px-4 py-3 w-10"><div className="w-4 h-4 animate-shimmer rounded" /></td>
      {Array.from({ length: cols - 1 }).map((_, i) => (
        <td key={i} className="px-4 py-3">
          <div className={`h-3.5 animate-shimmer rounded ${widths[i % widths.length]}`} />
        </td>
      ))}
    </tr>
  )
}

export function SkeletonTable({ rows = 5, cols = 5 }: { rows?: number; cols?: number }) {
  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="border-b border-surface-600 bg-surface-900/60">
          <th className="w-10 px-4 py-3" />
          {Array.from({ length: cols - 1 }).map((_, i) => (
            <th key={i} className="px-4 py-3">
              <div className="h-3 animate-shimmer rounded w-16" />
            </th>
          ))}
        </tr>
      </thead>
      <tbody className="divide-y divide-surface-700">
        {Array.from({ length: rows }).map((_, i) => (
          <SkeletonRow key={i} cols={cols} />
        ))}
      </tbody>
    </table>
  )
}
