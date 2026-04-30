import { useState, useRef, useEffect } from 'react'
import { createPortal } from 'react-dom'

interface Props {
  content: string
  children: React.ReactNode
}

export default function Tooltip({ content, children }: Props) {
  const [visible, setVisible] = useState(false)
  const [pos, setPos] = useState({ top: 0, left: 0 })
  const ref = useRef<HTMLSpanElement>(null)

  const show = () => {
    if (!ref.current) return
    const r = ref.current.getBoundingClientRect()
    setPos({ top: r.bottom + 6, left: r.left + r.width / 2 })
    setVisible(true)
  }

  useEffect(() => {
    if (!visible) return
    const hide = () => setVisible(false)
    window.addEventListener('scroll', hide, true)
    return () => window.removeEventListener('scroll', hide, true)
  }, [visible])

  return (
    <>
      <span ref={ref} onMouseEnter={show} onMouseLeave={() => setVisible(false)} className="inline-flex">
        {children}
      </span>
      {visible && createPortal(
        <div
          className="fixed z-[9999] max-w-xs px-2.5 py-1.5 bg-surface-700 border border-surface-500 rounded-md shadow-lg text-xs text-surface-200 pointer-events-none"
          style={{ top: pos.top, left: pos.left, transform: 'translateX(-50%)' }}
        >
          {content}
        </div>,
        document.body
      )}
    </>
  )
}
