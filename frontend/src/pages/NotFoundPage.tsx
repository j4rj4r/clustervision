import { useNavigate } from 'react-router-dom'
import { FileQuestion } from 'lucide-react'
import Button from '../components/ui/Button'

export default function NotFoundPage() {
  const navigate = useNavigate()

  return (
    <div className="flex flex-col items-center justify-center h-full gap-5 text-center px-6">
      <FileQuestion size={52} className="text-surface-600" />
      <div>
        <p className="text-4xl font-bold text-surface-200">404</p>
        <p className="text-sm text-surface-400 mt-2">This page doesn't exist.</p>
      </div>
      <Button variant="secondary" onClick={() => navigate('/users')}>
        Back to Users
      </Button>
    </div>
  )
}
