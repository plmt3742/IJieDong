/** Promise wrapper around wx.request with envelope, auth and error handling. */
import type { ApiErrorBody, Meta } from '../types/api';
import { clearSession, getToken } from '../utils/auth';
import { resolveApiUrl } from './config';

export type HttpMethod = 'GET' | 'POST' | 'PATCH' | 'PUT' | 'DELETE';

export interface RequestOptions {
  method?: HttpMethod;
  data?: unknown;
  showLoading?: boolean;
  timeout?: number;
  headers?: Record<string, string>;
}

interface RawEnvelope<T> {
  data: T;
  meta: Meta;
}

export class ApiError extends Error {
  code: string;
  status: number;
  requestId: string;
  details: Record<string, unknown> | null;

  constructor(
    code: string,
    message: string,
    status = 0,
    requestId = '',
    details: Record<string, unknown> | null = null
  ) {
    super(message);
    this.name = 'ApiError';
    this.code = code;
    this.status = status;
    this.requestId = requestId;
    this.details = details;
  }
}

const FALLBACK_MESSAGES: Record<string, string> = {
  AUTH_REQUIRED: '请先登录后再操作。',
  AUTH_INVALID: '登录状态已失效，请重新登录。',
  USER_DISABLED: '账号已被禁用，请联系管理员。',
  FORBIDDEN: '当前身份没有访问权限。',
  VALIDATION_ERROR: '提交内容校验未通过。',
  RATE_LIMITED: '操作过于频繁，请稍后再试。',
  APPLICATION_DUPLICATE: '该手机号已有待审申请或账号。',
  APPLICATION_NOT_PENDING: '该申请已被处理。',
  CANNOT_APPROVE_SELF: '不能审批本人申请。',
  LAST_ADMIN_PROTECTED: '最后一个管理员不可禁用或降级。',
  EXPORT_FORBIDDEN: '当前身份不可导出，请先申请账号。',
  EXPORT_FORMAT_REQUIRED: '请先选择导出格式。',
  NOT_FOUND: '接口或资源不存在。',
  METHOD_NOT_ALLOWED: '接口暂未开放。',
  NOT_READY: '服务尚未就绪。',
  AI_TIMEOUT: '查询超时，请重试。',
  AI_INVALID_OUTPUT: '回答校验未通过，请重试。',
  DATA_NOT_FOUND: '当前没有该指标或年份的数据。',
  INDICATOR_NOT_NUMERIC: '文本指标不支持排名或对比。',
  NETWORK_ERROR: '网络连接失败，请检查网络后重试。',
  API_BASE_URL_MISSING: '未配置 API 地址，请在本地配置后重试。',
  INVALID_RESPONSE: '服务返回格式异常。',
  INTERNAL_ERROR: '服务暂时不可用，请稍后重试。',
};

let loadingCount = 0;

function beginLoading(): void {
  if (loadingCount === 0) {
    wx.showLoading({ title: '加载中', mask: false });
  }
  loadingCount += 1;
}

function endLoading(): void {
  loadingCount = Math.max(0, loadingCount - 1);
  if (loadingCount === 0) {
    wx.hideLoading();
  }
}

export function buildQuery(
  params: Record<string, string | number | boolean | null | undefined>
): string {
  const parts: string[] = [];
  Object.keys(params).forEach((key) => {
    const value = params[key];
    if (value === null || value === undefined || value === '') {
      return;
    }
    parts.push(`${encodeURIComponent(key)}=${encodeURIComponent(String(value))}`);
  });
  return parts.length ? `?${parts.join('&')}` : '';
}

export function requestWithMeta<T>(path: string, options: RequestOptions = {}): Promise<RawEnvelope<T>> {
  const url = resolveApiUrl(path);
  if (!url) {
    return Promise.reject(
      new ApiError('API_BASE_URL_MISSING', FALLBACK_MESSAGES.API_BASE_URL_MISSING)
    );
  }
  const method = options.method || 'GET';
  const token = getToken();
  const header: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  };
  if (token) {
    header.Authorization = `Bearer ${token}`;
  }
  if (options.showLoading) {
    beginLoading();
  }

  return new Promise<RawEnvelope<T>>((resolve, reject) => {
    wx.request<RawEnvelope<T>>({
      url,
      // The public typings omit PATCH while the runtime accepts it; keep the
      // documented /admin/users PATCH path and verify on a real device.
      method: method as unknown as WechatMiniprogram.RequestOption['method'],
      data: options.data as WechatMiniprogram.IAnyObject | undefined,
      header,
      timeout: options.timeout || 20000,
      success: (res) => {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          const body = res.data;
          if (body && typeof body === 'object' && typeof body.data !== 'undefined') {
            resolve(body);
            return;
          }
          reject(
            new ApiError(
              'INVALID_RESPONSE',
              FALLBACK_MESSAGES.INVALID_RESPONSE,
              res.statusCode
            )
          );
          return;
        }

        const body = res.data as unknown as ApiErrorBody;
        const error = body && body.error ? body.error : null;
        const code = error && error.code ? error.code : statusCodeToCode(res.statusCode);
        const message =
          (error && error.message) || FALLBACK_MESSAGES[code] || '请求失败，请稍后重试。';
        const requestId =
          (body && body.request_id) ||
          (typeof res.header['X-Request-ID'] === 'string' ? res.header['X-Request-ID'] : '');

        if (res.statusCode === 401 || code === 'USER_DISABLED') {
          clearSession();
        }

        reject(
          new ApiError(
            code,
            message,
            res.statusCode,
            requestId,
            error && error.details ? error.details : null
          )
        );
      },
      fail: (err) => {
        const message = err.errMsg && err.errMsg.indexOf('timeout') >= 0
          ? FALLBACK_MESSAGES.AI_TIMEOUT
          : FALLBACK_MESSAGES.NETWORK_ERROR;
        reject(new ApiError('NETWORK_ERROR', message));
      },
      complete: () => {
        if (options.showLoading) {
          endLoading();
        }
      },
    });
  });
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const envelope = await requestWithMeta<T>(path, options);
  return envelope.data;
}

/** Optional endpoints can be missing while B-002 lands in parallel. */
export function isFeatureUnavailable(error: unknown): boolean {
  if (!(error instanceof ApiError)) {
    return false;
  }
  if (error.code === 'NETWORK_ERROR' || error.code === 'API_BASE_URL_MISSING') {
    return true;
  }
  return (
    error.status === 404 ||
    error.status === 405 ||
    error.status === 501 ||
    error.status === 503 ||
    error.code === 'METHOD_NOT_ALLOWED' ||
    error.code === 'NOT_READY'
  );
}

export function isAuthError(error: unknown): boolean {
  return (
    error instanceof ApiError &&
    (error.status === 401 || error.code === 'AUTH_REQUIRED' || error.code === 'AUTH_INVALID')
  );
}

export function toErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.code === 'NETWORK_ERROR' && error.message) {
      return error.message;
    }
    return FALLBACK_MESSAGES[error.code] || error.message || '请求失败，请稍后重试。';
  }
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return '请求失败，请稍后重试。';
}

export function toErrorRequestId(error: unknown): string {
  return error instanceof ApiError ? error.requestId : '';
}

function statusCodeToCode(statusCode: number): string {
  if (statusCode === 400 || statusCode === 422) {
    return 'VALIDATION_ERROR';
  }
  if (statusCode === 401) {
    return 'AUTH_REQUIRED';
  }
  if (statusCode === 403) {
    return 'FORBIDDEN';
  }
  if (statusCode === 404) {
    return 'NOT_FOUND';
  }
  if (statusCode === 405) {
    return 'METHOD_NOT_ALLOWED';
  }
  if (statusCode === 429) {
    return 'RATE_LIMITED';
  }
  if (statusCode >= 500) {
    return 'INTERNAL_ERROR';
  }
  return 'HTTP_ERROR';
}
