/** Runtime configuration. No secrets, no production domain hardcoded. */
import { getStorage, setStorage, STORAGE_KEYS } from '../utils/storage';

export const APP_NAME = 'i揭东';
export const APP_VERSION = '0.1.0-demo';
export const DEMO_MODE = true;
export const DEFAULT_PERIOD_YEAR = 2025;
export const DEMO_SOURCE_LABEL = '演示种子数据（合成）';
export const WATERMARK_TEXT = '演示数据·内部资料';

/** Empty by default in release builds; configure per environment. */
const DEVELOPMENT_BASE_URL = 'http://127.0.0.1:8000/api/v1';
const RELEASE_BASE_URL = '';

/** Fill locally before device tests. Never commit a real personal number. */
export const MAINTAINER_PHONE = '';
export const MAINTAINER_PHONE_DISPLAY = MAINTAINER_PHONE || '待配置';

export const API_PATHS = {
  dashboardOverview: '/dashboard/overview',
  regions: '/regions',
  regionTree: '/regions/tree',
  regionDetail: '/regions',
  regionProfile: '/regions',
  indicators: '/indicators',
  dataValues: '/data-values',
  dataValuesRank: '/data-values/rank',
  dataValuesCompare: '/data-values/compare',
  aiChat: '/ai/chat',
  aiSessions: '/ai/sessions',
  authMe: '/auth/me',
  authLogin: '/auth/login',
  authApply: '/auth/apply',
  authApplicationStatus: '/auth/application-status',
  authLogout: '/auth/logout',
  adminApplications: '/admin/applications',
  adminUsers: '/admin/users',
  adminAuditLogs: '/admin/audit-logs',
  exports: '/exports',
} as const;

export function getApiBaseUrl(): string {
  const override = getStorage<string>(STORAGE_KEYS.apiBaseUrl, '').trim();
  if (override) {
    return trimTrailingSlash(override);
  }
  try {
    const account = wx.getAccountInfoSync();
    const envVersion = account.miniProgram.envVersion;
    if (envVersion === 'develop') {
      return DEVELOPMENT_BASE_URL;
    }
  } catch (error) {
    console.warn('[config] account info unavailable', error);
    return DEVELOPMENT_BASE_URL;
  }
  return RELEASE_BASE_URL;
}

export function setApiBaseUrl(url: string): void {
  setStorage(STORAGE_KEYS.apiBaseUrl, trimTrailingSlash(url.trim()));
}

export function resolveApiUrl(path: string): string {
  const base = getApiBaseUrl();
  if (!base) {
    return '';
  }
  if (/^https?:\/\//i.test(path)) {
    return path;
  }
  return `${base}${path.startsWith('/') ? path : `/${path}`}`;
}

function trimTrailingSlash(url: string): string {
  return url.replace(/\/+$/, '');
}
