import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface ClusterStore {
  activeCluster: string
  setActiveCluster: (name: string) => void
}

export const useClusterStore = create<ClusterStore>()(
  persist(
    (set) => ({
      activeCluster: 'local',
      setActiveCluster: (name) => set({ activeCluster: name }),
    }),
    { name: 'clustervision-active-cluster' }
  )
)
