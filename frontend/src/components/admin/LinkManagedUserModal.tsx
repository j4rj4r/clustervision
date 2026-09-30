import { useState } from 'react'
import Modal from '../ui/Modal'
import Button from '../ui/Button'
import Select from '../ui/Select'
import { useUsers } from '../../hooks/useUsers'
import { useSetLink, useClearLink } from '../../hooks/useLink'
import type { LinkedUser } from '../../api/auth'

const userKey = (u: { name: string; namespace?: string }) => `${u.namespace ?? ''}/${u.name}`

interface Props {
  username: string
  currentLink: LinkedUser | null
  onClose: () => void
}

export default function LinkManagedUserModal({ username, currentLink, onClose }: Props) {
  const { data: usersData, isLoading } = useUsers()
  const users = usersData?.users ?? []
  const setLink = useSetLink(username)
  const clearLink = useClearLink(username)

  const [selectedKey, setSelectedKey] = useState(currentLink ? `${currentLink.namespace}/${currentLink.name}` : '')

  const handleSave = () => {
    if (!selectedKey) return
    const [namespace, name] = selectedKey.split('/')
    setLink.mutate({ name, namespace }, { onSuccess: onClose })
  }

  return (
    <Modal open onClose={onClose} title={`Kubernetes identity for ${username}`} size="sm" closeOnBackdrop={false}>
      <div className="space-y-4">
        <p className="text-xs text-surface-500">
          Linking doesn't change what {username} can do — generating a kubeconfig for any managed user already
          only requires operator access on that cluster. It just lets them jump straight to their own kubeconfig
          from the Dashboard instead of finding it manually. Picks from managed users on the currently active cluster.
        </p>

        {isLoading ? (
          <div className="text-sm text-surface-400 text-center py-6">Loading...</div>
        ) : users.length === 0 ? (
          <div className="text-sm text-surface-400 text-center py-6">No managed users on this cluster yet.</div>
        ) : (
          <Select
            label="Managed user"
            value={selectedKey}
            onChange={(e) => setSelectedKey(e.target.value)}
            options={[
              { value: '', label: 'Not linked' },
              ...users.map((u) => ({ value: userKey(u), label: `${u.name} (${u.namespace}, ${u.user_type})` })),
            ]}
          />
        )}

        <div className="flex gap-3 pt-1">
          <Button variant="secondary" size="sm" className="flex-1" onClick={onClose}>Cancel</Button>
          {currentLink && (
            <Button
              variant="danger"
              size="sm"
              loading={clearLink.isPending}
              onClick={() => clearLink.mutate(undefined, { onSuccess: onClose })}
            >
              Unlink
            </Button>
          )}
          <Button
            size="sm"
            className="flex-1"
            loading={setLink.isPending}
            disabled={!selectedKey}
            onClick={handleSave}
          >
            Save
          </Button>
        </div>
      </div>
    </Modal>
  )
}
