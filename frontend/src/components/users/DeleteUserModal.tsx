import { Trash2 } from 'lucide-react'
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
      <div className="space-y-4">
        <p className="text-sm text-slate-300">
          Are you sure you want to delete <span className="font-mono font-semibold text-slate-100">{user?.name}</span>?
          This will remove the CSR/ServiceAccount and all ClusterVision-managed bindings.
        </p>
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
