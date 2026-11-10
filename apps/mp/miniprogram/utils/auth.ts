/** Authentication, identity and guest quota helpers. */
import type {
  ApplicationStatus,
  ApplicationStatusResponse,
  AuthUser,
  UserRole,
} from '../types/api';
import type { IdentityView } from '../types/models';
import {
  getStorage,
  removeStorage,
  setStorage,
  STORAGE_KEYS,
} from './storage';

export interface StoredApplication extends ApplicationStatusResponse {
  phone?: string;
  reason?: string;
  demo?: boolean;
}

export interface GuestAiUsage {
  date: string;
  count: number;
}

const GUEST_AI_DAILY_LIMIT = 5;

type AuthListener = () => void;
const listeners: AuthListener[] = [];

export function subscribeAuth(listener: AuthListener): () => void {
  listeners.push(listener);
  return () => {
    const index = listeners.indexOf(listener);
    if (index >= 0) {
      listeners.splice(index, 1);
    }
  };
}

export function notifyAuthChanged(): void {
  listeners.slice().forEach((listener) => {
    try {
      listener();
    } catch (error) {
      console.warn('[auth] listener failed', error);
    }
  });
}

export function getToken(): string {
  return getStorage<string>(STORAGE_KEYS.token, '');
}

export function setToken(token: string): void {
  setStorage(STORAGE_KEYS.token, token);
}

export function getUser(): AuthUser | null {
  return getStorage<AuthUser | null>(STORAGE_KEYS.user, null);
}

export function setUser(user: AuthUser): void {
  setStorage(STORAGE_KEYS.user, user);
}

export function clearSession(): void {
  removeStorage(STORAGE_KEYS.token);
  removeStorage(STORAGE_KEYS.user);
  notifyAuthChanged();
}

export function clearAll(): void {
  removeStorage(STORAGE_KEYS.token);
  removeStorage(STORAGE_KEYS.user);
  removeStorage(STORAGE_KEYS.application);
  removeStorage(STORAGE_KEYS.aiUsage);
  notifyAuthChanged();
}

export function getApplication(): StoredApplication | null {
  return getStorage<StoredApplication | null>(STORAGE_KEYS.application, null);
}

export function saveApplication(application: StoredApplication): void {
  setStorage(STORAGE_KEYS.application, application);
  notifyAuthChanged();
}

export function clearApplication(): void {
  removeStorage(STORAGE_KEYS.application);
  notifyAuthChanged();
}

export function isApplicant(): boolean {
  if (getUser()) {
    return false;
  }
  const application = getApplication();
  if (!application) {
    return false;
  }
  return (
    application.status === 'pending' ||
    application.status === 'approved' ||
    application.status === 'rejected'
  );
}

export function canAccessData(): boolean {
  const user = getUser();
  if (user) {
    return user.status === 'active';
  }
  return !isApplicant();
}

export function canExport(): boolean {
  const user = getUser();
  return !!user && user.status === 'active';
}

export function getIdentity(): IdentityView {
  const user = getUser();
  const application = getApplication();
  const applicant = isApplicant();
  const role: UserRole = user ? user.role : applicant ? 'applicant' : 'guest';
  const applicationStatus: ApplicationStatus = user
    ? user.status === 'active'
      ? 'active'
      : 'disabled'
    : application
      ? application.status
      : 'none';
  const exportAllowed = !!user && user.status === 'active';
  const manageAllowed = !!user && (user.role === 'admin' || user.role === 'approver');
  return {
    role,
    label: roleLabel(role),
    name: user ? user.display_name : application ? application.display_name || '' : '',
    unit: user ? user.unit : application ? application.unit || '' : '',
    isGuest: role === 'guest',
    isApplicant: role === 'applicant',
    isAdmin: !!user && user.role === 'admin',
    isApprover: !!user && user.role === 'approver',
    canExport: exportAllowed,
    canManage: manageAllowed,
    canUseAi: !applicant && (!user || user.status === 'active'),
    applicationStatus,
    applicationNo: application ? application.application_no : '',
  };
}

export function roleLabel(role: UserRole): string {
  const labels: Record<UserRole, string> = {
    guest: '游客',
    applicant: '申请者',
    viewer: '查看者',
    editor: '编辑者',
    admin: '管理员',
    approver: '审批者',
  };
  return labels[role];
}

export function getGuestAiUsage(): GuestAiUsage {
  const today = dateKey(new Date());
  const usage = getStorage<GuestAiUsage>(STORAGE_KEYS.aiUsage, { date: today, count: 0 });
  if (usage.date !== today) {
    return { date: today, count: 0 };
  }
  return usage;
}

export function getGuestAiRemaining(): number {
  return Math.max(0, GUEST_AI_DAILY_LIMIT - getGuestAiUsage().count);
}

export function canUseGuestAi(): boolean {
  return getGuestAiRemaining() > 0;
}

export function recordGuestAiUse(): GuestAiUsage {
  const usage = getGuestAiUsage();
  const next = { date: usage.date, count: usage.count + 1 };
  setStorage(STORAGE_KEYS.aiUsage, next);
  return next;
}

export function guestAiLimit(): number {
  return GUEST_AI_DAILY_LIMIT;
}

export function guestQuotaText(): string {
  const remaining = getGuestAiRemaining();
  return `游客每日可使用 AI ${GUEST_AI_DAILY_LIMIT} 次，今日剩余 ${remaining} 次。`;
}

function dateKey(date: Date): string {
  const month = date.getMonth() + 1;
  const day = date.getDate();
  const monthText = month < 10 ? `0${month}` : `${month}`;
  const dayText = day < 10 ? `0${day}` : `${day}`;
  return `${date.getFullYear()}-${monthText}-${dayText}`;
}
