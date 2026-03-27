export interface TokenHistoryEntry {
  id: string
  user: string
  user_type: string
  namespace: string
  generated_at: string
}

export interface SaTokenInfo {
  secret_name: string
  sa_name: string
  namespace: string
  created_at: string | null
  token_present: boolean
}
