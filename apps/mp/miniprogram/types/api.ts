/** API contracts used by the mini program. Values mirror docs/agent/05 and 23/25. */
import type { ChartSpec } from './chart';

export interface Meta {
  request_id: string;
}

export interface PageMeta extends Meta {
  page: number;
  page_size: number;
  total: number;
  has_next: boolean;
}

export interface RankMeta extends Meta {
  indicator_code: string;
  period_year: number;
  level: string;
  order: string;
  limit: number;
  include_development_zones: boolean;
}

export interface CompareMeta extends Meta {
  indicator_code: string;
  period_year: number;
  requested_count: number;
}

export interface ItemEnvelope<T> {
  data: T;
  meta: Meta;
}

export interface PageEnvelope<T> {
  data: T[];
  meta: PageMeta;
}

export interface RankEnvelope<T> {
  data: T[];
  meta: RankMeta;
}

export interface CompareEnvelope<T> {
  data: T[];
  meta: CompareMeta;
}

export interface ApiErrorBody {
  error: {
    code: string;
    message: string;
    details?: Record<string, unknown> | null;
  };
  request_id?: string;
}

export type RegionLevel = 'district' | 'town' | 'village';
export type RegionCategory = 'administrative' | 'development_zone';

export interface Region {
  id: number;
  code: string;
  name: string;
  level: RegionLevel;
  category: RegionCategory;
  parent_id: number | null;
  sort_order: number;
  enabled: boolean;
}

export interface RegionDetail extends Region {
  parent?: Region | null;
}

export interface RegionTree extends Region {
  children: RegionTree[];
}

export interface ProfileMetric {
  indicator_id: number;
  code: string;
  name: string;
  unit: string;
  value_number: number | null;
  quality_status: string;
  period_year: number;
}

export interface RegionProfile {
  region: Region;
  parent?: Region | null;
  intro: string | null;
  feature: string | null;
  metrics: ProfileMetric[];
  applicable_indicator_codes: string[];
  data_as_of: string | null;
}

export interface Indicator {
  id: number;
  code: string;
  name: string;
  unit: string;
  value_type: 'long_text' | 'decimal' | 'integer' | 'currency';
  category: string | null;
  applicable_levels: RegionLevel[];
  applicable_region_categories: RegionCategory[] | null;
  aggregation: string;
  precision: number;
  max_length: number | null;
  direction: string;
  description: string | null;
  sort_order: number;
  enabled: boolean;
  status: string;
  version: number;
}

export interface DataValue {
  id: number;
  region_id: number;
  region_code: string;
  region_name: string;
  region_level: RegionLevel;
  region_category: RegionCategory;
  indicator_id: number;
  indicator_code: string;
  indicator_name: string;
  unit: string;
  period_year: number;
  value_number: number | null;
  value_text: string | null;
  quality_status: string;
  status: string;
  updated_at: string;
}

export interface RankItem {
  rank: number;
  region_id: number;
  region_code: string;
  region_name: string;
  value_number: number;
  unit: string;
}

export interface CompareItem {
  region_id: number;
  region_code: string;
  region_name: string;
  value_number: number | null;
  quality_status: string;
  unit: string;
  diff_from_first: number | null;
  diff_pct_from_first: number | null;
}

export interface DashboardMetric {
  code: string;
  label: string;
  unit: string;
  value_number: number | null;
  quality_status: string;
}

export interface DashboardOverview {
  period_year: number;
  town_count: number;
  coverage: number | null;
  data_as_of: string | null;
  metrics: DashboardMetric[];
}

export type UserRole = 'guest' | 'applicant' | 'viewer' | 'editor' | 'admin' | 'approver';
export type AccountRole = Exclude<UserRole, 'guest' | 'applicant'>;
export type UserStatus = 'active' | 'disabled';

export interface AuthUser {
  id: number;
  username?: string;
  display_name: string;
  unit: string;
  phone?: string;
  phone_masked?: string;
  role: AccountRole;
  status: UserStatus;
  created_at?: string;
  last_login_at?: string | null;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: AuthUser;
}

export type ApplicationStatus = 'none' | 'pending' | 'approved' | 'rejected' | 'active' | 'disabled';

export interface ApplicationPayload {
  display_name: string;
  unit: string;
  phone: string;
  reason: string;
  privacy_consent: boolean;
}

export interface ApplicationSubmitResult {
  application_no: string;
  status: ApplicationStatus;
  status_token: string;
  submitted_at: string;
}

export interface ApplicationTimelineItem {
  key: string;
  label: string;
  time?: string | null;
  state: 'done' | 'current' | 'pending' | 'failed';
  description?: string;
}

export interface ApplicationStatusResponse {
  application_no: string;
  status: ApplicationStatus;
  status_token?: string;
  display_name?: string;
  unit?: string;
  phone_masked?: string;
  submitted_at: string;
  reviewed_at?: string | null;
  reject_reason?: string | null;
  resubmit_available_at?: string | null;
  resubmit_count?: number;
  timeline?: ApplicationTimelineItem[];
  demo?: boolean;
}

export interface AdminApplication {
  id: number;
  application_no: string;
  display_name: string;
  unit: string;
  phone_masked?: string;
  phone?: string;
  reason?: string;
  status: ApplicationStatus;
  submitted_at: string;
  reviewed_at?: string | null;
  resubmit_count?: number;
  privacy_version?: string;
  is_self?: boolean;
}

export interface AdminUser {
  id: number;
  username?: string;
  display_name: string;
  unit: string;
  phone_masked?: string;
  role: AccountRole;
  status: UserStatus;
  last_login_at?: string | null;
}

export interface AuditLogItem {
  id: number;
  created_at: string;
  actor_name?: string;
  actor?: string;
  action: string;
  resource_type: string;
  resource_id?: string | number;
  result?: string;
  ip?: string;
}

export interface Citation {
  citation_id?: string;
  indicator?: string;
  indicator_name?: string;
  indicator_id?: number;
  indicator_code?: string;
  region?: string;
  region_id?: number;
  region_code?: string;
  region_name?: string;
  period?: string | number;
  region_level?: string;
  source?: string;
  data_as_of?: string;
}

export type AnswerBlockType =
  | 'summary'
  | 'metric_grid'
  | 'chart'
  | 'table'
  | 'ranking'
  | 'source'
  | 'notice'
  | 'actions';

export interface MetricGridItem {
  label: string;
  value: number | string | null;
  unit?: string;
  year?: number | string;
  quality_status?: string;
  display?: string;
}

export interface RankingEntry {
  rank: number;
  name: string;
  value: number | null;
  unit?: string;
}

export type AnswerActionType = 'navigate' | 'export' | 'apply' | 'retry';

export interface AnswerAction {
  key: string;
  label: string;
  type: AnswerActionType;
  url?: string;
  indicator_id?: number;
  indicator_code?: string;
  region_id?: number;
  period?: string | number;
}

export interface AnswerTableRow {
  id: number;
  cells: string[];
}

export interface AnswerRankingView {
  rank: number;
  name: string;
  value: string;
}

export interface AnswerBlock {
  type: AnswerBlockType;
  key?: string;
  title?: string;
  text?: string;
  chart?: ChartSpec | null;
  metrics?: MetricGridItem[];
  columns?: string[];
  rows?: Array<Array<string | number | null>>;
  ranking?: RankingEntry[];
  citations?: Citation[];
  actions?: AnswerAction[];
  source?: string;
  level?: 'info' | 'warning' | 'error' | 'success';
  tableColumns?: string[];
  tableRows?: AnswerTableRow[];
  rankingView?: AnswerRankingView[];
}

export interface AIChatRequest {
  session_id?: number | null;
  question: string;
  context?: {
    period?: string;
    region_id?: number;
    indicator_id?: number;
  };
}

export interface AIChatResponse {
  session_id: number | null;
  message_id: number | null;
  answer_id?: string;
  answer_markdown?: string;
  blocks?: AnswerBlock[];
  chart_spec?: ChartSpec | null;
  citations?: Citation[];
  follow_up_questions?: string[];
  status?: 'done' | 'refused' | 'no_data';
  demo?: boolean;
}

export type ExportFormat = 'png' | 'pdf' | 'xlsx' | 'csv';

export interface ExportSourceDescriptor {
  region_id?: number;
  region_name?: string;
  indicator_id?: number;
  indicator_code?: string;
  indicator_name?: string;
  period_year?: number;
  unit?: string;
}

export interface ExportCreateRequest {
  source_type: 'answer' | 'report';
  source_id?: string;
  format: ExportFormat;
  title: string;
  options?: {
    orientation?: 'portrait' | 'landscape';
    include_citations?: boolean;
    watermark?: boolean;
    max_rows?: number;
  };
  source?: ExportSourceDescriptor;
}

export type ExportJobStatus = 'queued' | 'running' | 'ready' | 'failed' | 'expired';

export interface ExportJob {
  export_id: string;
  status: ExportJobStatus;
  progress?: number;
  format: ExportFormat;
  title?: string;
  file_size?: number | null;
  sha256?: string | null;
  download_url?: string | null;
  expires_at?: string | null;
  error?: string | { code?: string; message?: string } | null;
  created_at?: string;
}

export interface AdminApplicationQuery {
  status?: string;
  q?: string;
  page?: number;
  page_size?: number;
}

export interface AdminUserQuery {
  q?: string;
  status?: string;
  page?: number;
  page_size?: number;
}

export interface PageResult<T> {
  items: T[];
  meta: PageMeta;
}
