export type UserType = 'certificate' | 'service_account'

export interface User {
  name: string
  user_type: UserType
  groups: string[]
  namespace: string
  created_at: string
  cert_expiry?: string
  csr_name?: string
  imported?: boolean
}

export interface UserWithCredentials extends User {
  private_key_pem?: string
  certificate_pem?: string
}

export interface UserList {
  users: User[]
  total: number
}

export interface CreateUserPayload {
  name: string
  user_type: UserType
  groups: string[]
  namespace: string
}

export interface DeleteUserPayload {
  username: string
  userType: UserType
  namespace?: string
}
