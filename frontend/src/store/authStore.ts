import { create } from 'zustand'

export type RoleName = 'viewer' | 'operator' | 'approver' | 'admin'

// The instance pseudo-scope — governs login accounts, cluster registry,
// Vault config, audit log, and JIT policy config. Real scopes are cluster
// names (or "local"). No entry for a scope means no access to it at all.
export const INSTANCE_SCOPE = '_instance'

export interface AuthUser {
  username: string
  roles: Record<string, RoleName>
}

interface AuthStore {
  user: AuthUser | null
  accessToken: string | null
  setAuth: (user: AuthUser, token: string) => void
  setAccessToken: (token: string) => void
  clearAuth: () => void
  isInstanceAdmin: () => boolean
  roleFor: (scope: string) => RoleName | undefined
  canWrite: (scope: string) => boolean
  hasAnyClusterAccess: () => boolean
}

export const useAuthStore = create<AuthStore>()((set, get) => ({
  user: null,
  accessToken: null,
  setAuth: (user, accessToken) => set({ user, accessToken }),
  setAccessToken: (accessToken) => set({ accessToken }),
  clearAuth: () => set({ user: null, accessToken: null }),
  isInstanceAdmin: () => get().user?.roles[INSTANCE_SCOPE] === 'admin',
  roleFor: (scope) => get().user?.roles[scope],
  canWrite: (scope) => {
    const role = get().user?.roles[scope]
    return role === 'operator' || role === 'admin'
  },
  hasAnyClusterAccess: () =>
    Object.keys(get().user?.roles ?? {}).some((scope) => scope !== INSTANCE_SCOPE),
}))
