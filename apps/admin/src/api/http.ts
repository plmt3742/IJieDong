import axios, { type AxiosError, type AxiosInstance, type AxiosRequestConfig } from 'axios'

import type { ApiMeta, ItemEnvelope, ListEnvelope, PageEnvelope } from './types'

export const TOKEN_KEY = 'ijd.admin.token'

const DEFAULT_BASE_URL = 'http://127.0.0.1:8000/api/v1'

export const API_BASE_URL: string = (import.meta.env.VITE_API_BASE_URL || DEFAULT_BASE_URL).replace(
  /\/+$/,
  '',
)

/* ---- Token storage ---- */

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token)
}

export function removeToken(): void {
  localStorage.removeItem(TOKEN_KEY)
}

/* ---- Error model ---- */

interface ApiErrorPayload {
  error?: {
    code?: unknown
    message?: unknown
    details?: unknown
  }
  request_id?: unknown
}

export class ApiError extends Error {
  readonly code: string
  readonly status: number
  readonly details: unknown
  readonly requestId: string | null

  constructor(input: {
    code: string
    message: string
    status: number
    details?: unknown
    requestId?: string | null
  }) {
    super(input.message)
    this.name = 'ApiError'
    this.code = input.code
    this.status = input.status
    this.details = input.details ?? null
    this.requestId = input.requestId ?? null
  }
}

export function toApiError(error: unknown): ApiError {
  if (error instanceof ApiError) return error
  if (axios.isAxiosError(error)) return fromAxiosError(error)
  if (error instanceof Error) {
    return new ApiError({ code: 'CLIENT_ERROR', message: error.message, status: 0 })
  }
  return new ApiError({ code: 'UNKNOWN_ERROR', message: '发生未知错误，请重试', status: 0 })
}

/* ---- Chinese message mapping ---- */

const CODE_MESSAGES: Record<string, string> = {
  AUTH_REQUIRED: '登录已失效，请重新登录',
  AUTH_INVALID: '登录已失效，请重新登录',
  USER_DISABLED: '账号已被禁用，请联系管理员',
  FORBIDDEN: '当前角色没有执行该操作的权限',
  VALIDATION_ERROR: '提交内容不合法，请检查后重试',
  RATE_LIMITED: '操作过于频繁，请稍后再试',
  APPLICATION_DUPLICATE: '该手机号已有待审申请或已存在账号',
  APPLICATION_NOT_PENDING: '该申请已被处理，请刷新列表',
  CANNOT_APPROVE_SELF: '不能审批本人的申请',
  LAST_ADMIN_PROTECTED: '不能禁用或降级最后一个管理员',
  EXPORT_FORBIDDEN: '当前身份不允许导出',
  NOT_FOUND: '资源不存在',
  DATA_NOT_FOUND: '没有查到对应数据',
  REGION_NOT_FOUND: '区域不存在',
  IMPORT_VALIDATION_FAILED: '导入校验未通过',
  IMPORT_FAILED: '导入执行失败',
  INDICATOR_NOT_NUMERIC: '该指标为文本类型，不支持排名或对比',
  INVALID_CREDENTIALS: '用户名或密码不正确',
  NOT_READY: '服务尚未就绪，请稍后重试',
  INTERNAL_ERROR: '服务内部错误，请稍后重试',
  NETWORK_ERROR: '网络请求失败，请检查后端服务是否已启动',
  TIMEOUT: '请求超时，请重试',
  CLIENT_ERROR: '请求未能完成，请重试',
  UNKNOWN_ERROR: '发生未知错误，请重试',
}

export function translateErrorCode(code: string, fallback?: string): string {
  const mapped = CODE_MESSAGES[code]
  if (mapped) return mapped
  if (fallback && fallback.trim().length > 0) return fallback
  return '请求未能完成，请重试'
}

/* ---- Unauthorized hook (wired in main.ts, avoids router/store cycles) ---- */

let unauthorizedHandler: (() => void) | null = null

export function setUnauthorizedHandler(handler: (() => void) | null): void {
  unauthorizedHandler = handler
}

function fromAxiosError(error: AxiosError): ApiError {
  const response = error.response
  if (!response) {
    const timedOut = error.code === 'ECONNABORTED'
    return new ApiError({
      code: timedOut ? 'TIMEOUT' : 'NETWORK_ERROR',
      message: timedOut ? CODE_MESSAGES.TIMEOUT : CODE_MESSAGES.NETWORK_ERROR,
      status: 0,
    })
  }

  const status = response.status
  const payload = (response.data ?? {}) as ApiErrorPayload
  const rawCode = typeof payload.error?.code === 'string' ? payload.error.code : ''
  const rawMessage = typeof payload.error?.message === 'string' ? payload.error.message : ''
  const requestId =
    typeof payload.request_id === 'string'
      ? payload.request_id
      : (response.headers['x-request-id'] as string | undefined) ?? null

  const fallbackCode = rawCode || (status === 404 ? 'NOT_FOUND' : status >= 500 ? 'INTERNAL_ERROR' : '')
  const code = fallbackCode || `HTTP_${status}`

  return new ApiError({
    code,
    message: translateErrorCode(code, rawMessage),
    status,
    details: payload.error?.details ?? null,
    requestId,
  })
}

/* ---- Axios instance ---- */

export const http: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 20000,
  headers: { Accept: 'application/json' },
})

http.interceptors.request.use((config) => {
  const token = getToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

http.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    const apiError = fromAxiosError(error)
    const url = error.config?.url ?? ''
    const isLoginRequest = url.includes('/auth/login')
    if (apiError.status === 401 && !isLoginRequest && unauthorizedHandler) {
      unauthorizedHandler()
    }
    return Promise.reject(apiError)
  },
)

/* ---- Typed request helpers ---- */

export async function getItem<T>(url: string, config?: AxiosRequestConfig): Promise<ItemEnvelope<T>> {
  const response = await http.get<ItemEnvelope<T>>(url, config)
  return response.data
}

export async function getList<T>(url: string, config?: AxiosRequestConfig): Promise<ListEnvelope<T>> {
  const response = await http.get<ListEnvelope<T>>(url, config)
  return response.data
}

export async function getPage<T>(url: string, config?: AxiosRequestConfig): Promise<PageEnvelope<T>> {
  const response = await http.get<PageEnvelope<T>>(url, config)
  return response.data
}

export async function postItem<T>(
  url: string,
  body?: unknown,
  config?: AxiosRequestConfig,
): Promise<ItemEnvelope<T>> {
  const response = await http.post<ItemEnvelope<T>>(url, body, config)
  return response.data
}

export async function patchItem<T>(
  url: string,
  body?: unknown,
  config?: AxiosRequestConfig,
): Promise<ItemEnvelope<T>> {
  const response = await http.patch<ItemEnvelope<T>>(url, body, config)
  return response.data
}

/** Human-readable message plus request id, ready for an alert body. */
export function describeApiError(error: unknown): string {
  const apiError = toApiError(error)
  const parts = [apiError.message]
  if (apiError.requestId) parts.push(`请求编号 ${apiError.requestId}`)
  else if (apiError.code && !apiError.code.startsWith('HTTP_')) parts.push(`错误码 ${apiError.code}`)
  return parts.join('；')
}

/** Secondary technical detail (code + status) kept out of the main message. */
export function describeApiErrorDetail(error: unknown): string {
  const apiError = toApiError(error)
  const labels: string[] = []
  if (apiError.status > 0) labels.push(`HTTP ${apiError.status}`)
  labels.push(apiError.code)
  if (apiError.requestId) labels.push(`request_id ${apiError.requestId}`)
  return labels.join(' · ')
}

/** Strip query-string undefined/empty values so URLs stay clean. */
export function cleanParams(params: Record<string, unknown>): Record<string, unknown> {
  const result: Record<string, unknown> = {}
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === '') continue
    result[key] = value
  }
  return result
}

export type { ApiMeta }
