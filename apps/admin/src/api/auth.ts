import { getItem, http, postItem } from './http'
import type { AuthUser, LoginPayload, LoginResult } from './types'

/** POST /auth/login */
export async function login(payload: LoginPayload): Promise<LoginResult> {
  const envelope = await postItem<LoginResult>('/auth/login', payload)
  return envelope.data
}

/** GET /auth/me */
export async function fetchMe(): Promise<AuthUser> {
  const envelope = await getItem<AuthUser>('/auth/me')
  return envelope.data
}

/** POST /auth/logout - returns 204 and server-side revocation is P1. */
export async function logout(): Promise<void> {
  try {
    await http.post('/auth/logout')
  } catch {
    // Client-side token removal is the Demo v0 contract.
  }
}
