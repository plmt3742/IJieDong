/** Local storage helpers with a single namespace and safe fallbacks. */

const PREFIX = 'ijd:';

export function getStorage<T>(key: string, fallback: T): T {
  try {
    const value: unknown = wx.getStorageSync(PREFIX + key);
    if (value === '' || value === undefined || value === null) {
      return fallback;
    }
    return value as T;
  } catch (error) {
    console.warn('[storage] read failed', key, error);
    return fallback;
  }
}

export function setStorage<T>(key: string, value: T): void {
  try {
    wx.setStorageSync(PREFIX + key, value);
  } catch (error) {
    console.warn('[storage] write failed', key, error);
  }
}

export function removeStorage(key: string): void {
  try {
    wx.removeStorageSync(PREFIX + key);
  } catch (error) {
    console.warn('[storage] remove failed', key, error);
  }
}

export const STORAGE_KEYS = {
  token: 'token',
  user: 'user',
  application: 'application',
  apiBaseUrl: 'api_base_url',
  aiUsage: 'ai_usage',
  preferredRegionLevel: 'preferred_region_level',
  pendingQuestion: 'pending_question',
} as const;
