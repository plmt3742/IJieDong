import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { fetchMe, login as loginRequest, logout as logoutRequest } from '@/api/auth'
import { getToken, removeToken, setToken } from '@/api/http'
import type { AuthUser, LoginPayload, LoginResult, Role } from '@/api/types'

const USER_KEY = 'ijd.admin.user'

/** Only summary fields are persisted; no secrets or tokens in this payload. */
function readStoredUser(): AuthUser | null {
  const raw = localStorage.getItem(USER_KEY)
  if (!raw) return null
  try {
    const parsed = JSON.parse(raw) as Partial<AuthUser>
    if (
      typeof parsed.id === 'number' &&
      typeof parsed.display_name === 'string' &&
      typeof parsed.role === 'string'
    ) {
      return {
        id: parsed.id,
        display_name: parsed.display_name,
        role: parsed.role as Role,
        unit: typeof parsed.unit === 'string' ? parsed.unit : null,
        username: typeof parsed.username === 'string' ? parsed.username : null,
      }
    }
  } catch {
    // Corrupt payload: treat as signed out.
  }
  return null
}

function persistUser(user: AuthUser | null): void {
  if (user) {
    localStorage.setItem(
      USER_KEY,
      JSON.stringify({
        id: user.id,
        display_name: user.display_name,
        role: user.role,
        unit: user.unit ?? null,
        username: user.username ?? null,
      }),
    )
  } else {
    localStorage.removeItem(USER_KEY)
  }
}

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(getToken())
  const user = ref<AuthUser | null>(readStoredUser())
  const submitting = ref(false)

  const isAuthenticated = computed(() => Boolean(token.value))
  const role = computed<Role | null>(() => user.value?.role ?? null)

  function applySession(result: LoginResult): void {
    token.value = result.access_token
    setToken(result.access_token)
    user.value = result.user
    persistUser(result.user)
  }

  async function login(payload: LoginPayload): Promise<LoginResult> {
    submitting.value = true
    try {
      const result = await loginRequest(payload)
      applySession(result)
      return result
    } finally {
      submitting.value = false
    }
  }

  async function loadMe(): Promise<AuthUser | null> {
    if (!token.value) return null
    const me = await fetchMe()
    user.value = me
    persistUser(me)
    return me
  }

  async function signOut(options: { notifyServer?: boolean } = {}): Promise<void> {
    if (options.notifyServer) {
      await logoutRequest()
    }
    token.value = null
    user.value = null
    removeToken()
    persistUser(null)
  }

  function clearSession(): void {
    token.value = null
    user.value = null
    removeToken()
    persistUser(null)
  }

  function hasRole(roles: Role[] | undefined): boolean {
    if (!roles || roles.length === 0) return true
    if (!user.value) return false
    return roles.includes(user.value.role)
  }

  return {
    token,
    user,
    submitting,
    isAuthenticated,
    role,
    login,
    loadMe,
    signOut,
    clearSession,
    hasRole,
  }
})
