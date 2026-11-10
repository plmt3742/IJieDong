/**
 * API types for the Demo v0 admin console.
 *
 * Shapes follow docs/agent/05-architecture.md API v0 and
 * docs/agent/23-auth-and-application-spec.md. Auth and /admin endpoints are
 * being added to the backend in parallel; optional fields stay optional so a
 * partial backend implementation degrades into explicit states instead of
 * runtime crashes.
 */

export type Role = 'guest' | 'applicant' | 'viewer' | 'editor' | 'admin' | 'approver'

export type RegionLevel = 'district' | 'town' | 'village'

export type QualityStatus =
  | 'missing'
  | 'not_applicable'
  | 'suppressed'
  | 'estimated'
  | 'provisional'
  | 'verified'

export interface ApiMeta {
  request_id?: string
  [key: string]: unknown
}

export interface PageMeta extends ApiMeta {
  page: number
  page_size: number
  total: number
  has_next: boolean
}

export interface ItemEnvelope<T> {
  data: T
  meta: ApiMeta
}

export interface ListEnvelope<T> {
  data: T[]
  meta: ApiMeta
}

export interface PageEnvelope<T> {
  data: T[]
  meta: PageMeta
}

export interface ListParams {
  page?: number
  page_size?: number
}

/* ---- Auth ---- */

export interface AuthUser {
  id: number
  display_name: string
  role: Role
  unit?: string | null
  username?: string | null
  status?: string | null
}

export interface LoginPayload {
  username: string
  password: string
}

export interface LoginResult {
  access_token: string
  token_type?: string
  expires_in?: number
  user: AuthUser
}

/* ---- Dashboard ---- */

export interface DashboardMetric {
  code: string
  label: string
  unit: string
  value_number: number | null
  quality_status: string
}

export interface DashboardOverview {
  period_year: number
  town_count: number
  coverage: number | null
  data_as_of: string | null
  metrics: DashboardMetric[]
}

/* ---- Regions / indicators ---- */

export interface Region {
  id: number
  code: string
  name: string
  level: RegionLevel | string
  category: string
  parent_id: number | null
  sort_order?: number
  enabled?: boolean
}

export interface Indicator {
  id: number
  code: string
  name: string
  unit: string
  value_type: string
  category?: string | null
  applicable_levels: string[]
  applicable_region_categories?: string[] | null
  aggregation?: string
  precision: number
  max_length?: number | null
  direction?: string
  description?: string | null
  sort_order?: number
  enabled?: boolean
  status?: string
  version?: number
}

/* ---- Data values ---- */

export interface DataValue {
  id: number
  region_id: number
  region_code: string
  region_name: string
  region_level: string
  region_category: string
  indicator_id: number
  indicator_code: string
  indicator_name: string
  unit: string
  period_year: number
  value_number: number | null
  value_text: string | null
  quality_status: QualityStatus | string
  status: string
  updated_at: string
}

export interface DataValueQuery {
  region_id?: number
  region_code?: string
  indicator_id?: number
  indicator_code?: string
  period_year?: number
  quality_status?: string
  page?: number
  page_size?: number
}

/* ---- Imports ---- */

export interface ImportJob {
  id: number
  job_type?: string
  filename: string | null
  status: string
  mode?: string
  total_rows?: number | null
  success_rows?: number | null
  error_rows?: number | null
  error_report_path?: string | null
  source_id?: number | null
  created_by?: number | null
  created_at?: string | null
  finished_at?: string | null
}

export interface ImportErrorItem {
  row?: number | null
  row_number?: number | null
  column?: string | null
  field?: string | null
  code?: string | null
  message?: string | null
  suggestion?: string | null
}

export interface ImportJobDetail extends ImportJob {
  errors?: ImportErrorItem[] | null
}

/* ---- Applications ---- */

export type ApplicationStatus = 'pending' | 'approved' | 'rejected'

export interface ApplicationItem {
  id: number
  application_no: string
  display_name: string
  unit: string
  phone?: string | null
  reason?: string | null
  status: ApplicationStatus
  reject_reason?: string | null
  resubmit_count?: number | null
  submitted_at?: string | null
  reviewed_by?: number | null
  reviewed_at?: string | null
  user_id?: number | null
  created_at?: string | null
  updated_at?: string | null
}

export interface ApproveApplicationPayload {
  role: Exclude<Role, 'guest' | 'applicant'>
  unit?: string
  note?: string
}

/** POST /admin/applications/{id}/approve response; initial_password is shown only once. */
export interface ApproveResult {
  application_id: number
  status: string
  user_id: number
  username: string
  role: string
  initial_password: string
}

/* ---- Users ---- */

export interface AdminUser {
  id: number
  username: string
  display_name: string
  unit?: string | null
  phone?: string | null
  role: Role
  status: 'active' | 'disabled' | string
  must_change_password?: boolean
  last_login_at?: string | null
  created_at?: string | null
}

export interface UserPatchPayload {
  role?: Exclude<Role, 'guest' | 'applicant'>
  status?: 'active' | 'disabled'
  unit?: string
}

/* ---- Audit ---- */

export interface AuditLog {
  id: number
  user_id?: number | null
  user_display_name?: string | null
  username?: string | null
  action: string
  resource_type?: string | null
  resource_id?: string | number | null
  detail?: unknown
  ip?: string | null
  user_agent?: string | null
  created_at: string
}

export interface AuditLogQuery extends ListParams {
  action?: string
  user_id?: number
  /** Sent for forward compatibility; the Demo v0 endpoint ignores date bounds. */
  date_from?: string
  date_to?: string
}
