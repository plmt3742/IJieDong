import type { ApplicationStatus, QualityStatus, Role } from '@/api/types'

export const ROLE_LABELS: Record<Role | string, string> = {
  guest: '游客',
  applicant: '申请者',
  viewer: '查看者',
  editor: '编辑者',
  admin: '管理员',
  approver: '审批者',
}

export const QUALITY_LABELS: Record<QualityStatus | string, string> = {
  missing: '暂无数据',
  not_applicable: '不适用',
  suppressed: '已抑制',
  estimated: '估算值',
  provisional: '暂定值',
  verified: '已核实',
}

export const QUALITY_TAG_TYPES: Record<string, 'success' | 'info' | 'warning' | 'danger' | ''> = {
  missing: 'info',
  not_applicable: 'info',
  suppressed: 'warning',
  estimated: 'warning',
  provisional: 'warning',
  verified: 'success',
}

export const PUBLISH_STATUS_LABELS: Record<string, string> = {
  draft: '草稿',
  published: '已发布',
  archived: '已归档',
}

export const IMPORT_STATUS_LABELS: Record<string, string> = {
  pending: '等待中',
  running: '执行中',
  success: '成功',
  partial: '部分成功',
  failed: '失败',
}

export const IMPORT_STATUS_TAG_TYPES: Record<string, 'success' | 'info' | 'warning' | 'danger' | ''> = {
  pending: 'info',
  running: 'warning',
  success: 'success',
  partial: 'warning',
  failed: 'danger',
}

export const APPLICATION_STATUS_LABELS: Record<ApplicationStatus | string, string> = {
  pending: '待审批',
  approved: '已批准',
  rejected: '已驳回',
}

export const APPLICATION_STATUS_TAG_TYPES: Record<
  string,
  'success' | 'info' | 'warning' | 'danger' | ''
> = {
  pending: 'warning',
  approved: 'success',
  rejected: 'danger',
}

export const USER_STATUS_LABELS: Record<string, string> = {
  active: '启用',
  disabled: '禁用',
}

export const LEVEL_LABELS: Record<string, string> = {
  district: '区',
  town: '镇街',
  village: '村居',
}

export const REGION_CATEGORY_LABELS: Record<string, string> = {
  administrative: '行政区',
  development_zone: '开发区/生态城',
}

export const VALUE_TYPE_LABELS: Record<string, string> = {
  long_text: '文本',
  integer: '整数',
  decimal: '小数',
  currency: '金额',
  number: '数值',
  boolean: '布尔',
  date: '日期',
  json: '结构化',
}

/** Thousands-separated number with a bounded number of decimals, no padding. */
export function formatNumber(value: number | null | undefined, precision = 2): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '暂无数据'
  const maximumFractionDigits = Math.min(Math.max(precision, 0), 6)
  return new Intl.NumberFormat('zh-CN', {
    minimumFractionDigits: 0,
    maximumFractionDigits,
  }).format(value)
}

/** Integer style used for population and counts. */
export function formatInteger(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '暂无数据'
  return new Intl.NumberFormat('zh-CN', { maximumFractionDigits: 0 }).format(value)
}

export function formatMeasure(
  value: number | null | undefined,
  unit: string | null | undefined,
  precision = 2,
): string {
  if (value === null || value === undefined) return '暂无数据'
  const text = formatNumber(value, precision)
  return unit ? `${text} ${unit}` : text
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return '—'
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) return value
  const pad = (input: number) => String(input).padStart(2, '0')
  return `${parsed.getFullYear()}-${pad(parsed.getMonth() + 1)}-${pad(parsed.getDate())} ${pad(
    parsed.getHours(),
  )}:${pad(parsed.getMinutes())}`
}

export function formatDateOnly(value: string | null | undefined): string {
  if (!value) return '—'
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) return value
  const pad = (input: number) => String(input).padStart(2, '0')
  return `${parsed.getFullYear()}-${pad(parsed.getMonth() + 1)}-${pad(parsed.getDate())}`
}

export function truncateText(value: string | null | undefined, max = 48): string {
  if (!value) return ''
  return value.length > max ? `${value.slice(0, max)}…` : value
}

/** Deterministic JSON rendering for drawers; sensitive keys are masked. */
export function toRedactedJson(value: unknown): string {
  if (value === null || value === undefined) return '—'
  return JSON.stringify(redactSensitive(value), null, 2)
}

const SENSITIVE_KEY = /pass(word)?|token|secret|hash|credential/i

export function redactSensitive(value: unknown): unknown {
  if (Array.isArray(value)) return value.map((item) => redactSensitive(item))
  if (value && typeof value === 'object') {
    const source = value as Record<string, unknown>
    const result: Record<string, unknown> = {}
    for (const [key, item] of Object.entries(source)) {
      result[key] = SENSITIVE_KEY.test(key) ? '***' : redactSensitive(item)
    }
    return result
  }
  return value
}
