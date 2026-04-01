import { TriangleAlert, Trash2 } from 'lucide-react'
import Modal from '../ui/Modal'
import Button from '../ui/Button'
import { useDeleteUser } from '../../hooks/useUsers'
import type { User } from '../../types/user'

interface Props {
  user: User | null
  onClose: () => void
}

export default function DeleteUserModal({ user, onClose }: Props) {
  const deleteUser = useDeleteUser()

  const handleDelete = () => {
    if (!user) return
    deleteUser.mutate(
      { username: user.name, userType: user.user_type, namespace: user.namespace },
      { onSuccess: onClose },
    )
  }

  return (
    <Modal open={!!user} onClose={onClose} title="Delete user" size="sm">
      <div className="space-y-5">
        <div className="flex gap-3 p-3 rounded-lg bg-red-950/40 border border-red-500/20">
          <TriangleAlert size={16} className="text-red-400 shrink-0 mt-0.5" />
          <p className="text-sm text-surface-200">
            Delete <span className="font-mono font-semibold text-surface-100">{user?.name}</span>?
            This will remove the {user?.user_type === 'certificate' ? 'CSR' : 'ServiceAccount'} and all managed role bindings. This cannot be undone.
          </p>
        </div>
        <div className="flex gap-3">
          <Button variant="secondary" onClick={onClose} className="flex-1">Cancel</Button>
          <Button variant="danger" onClick={handleDelete} loading={deleteUser.isPending} className="flex-1">
            <Trash2 size={14} /> Delete
          </Button>
        </div>
      </div>
    </Modal>
  )
}
