/** Typed API client. Paths follow docs/agent/05, 23 and 25. */
import type {
  AdminApplication,
  AdminApplicationQuery,
  AdminUser,
  AdminUserQuery,
  AIChatRequest,
  AIChatResponse,
  AnswerBlock,
  ApplicationPayload,
  ApplicationStatusResponse,
  ApplicationSubmitResult,
  AuditLogItem,
  AuthUser,
  CompareItem,
  DashboardOverview,
  DataValue,
  ExportCreateRequest,
  ExportJob,
  Indicator,
  LoginResponse,
  PageMeta,
  PageResult,
  RankItem,
  Region,
  RegionCategory,
  RegionDetail,
  RegionLevel,
  RegionProfile,
  RegionTree,
} from '../types/api';
import type { ChartSpec } from '../types/chart';
import { formatDate } from '../utils/format';
import { API_PATHS, DEFAULT_PERIOD_YEAR, resolveApiUrl } from './config';
import { buildQuery, request, requestWithMeta } from './request';

export interface RegionQuery {
  level?: RegionLevel;
  parent_id?: number;
  parent_code?: string;
  q?: string;
  category?: RegionCategory;
  enabled?: boolean;
  page?: number;
  page_size?: number;
}

export interface IndicatorQuery {
  level?: RegionLevel;
  category?: string;
  value_type?: string;
  enabled?: boolean;
  page?: number;
  page_size?: number;
}

export interface DataValueQuery {
  region_id?: number;
  region_code?: string;
  indicator_id?: number;
  indicator_code?: string;
  period_year?: number;
  quality_status?: string;
  page?: number;
  page_size?: number;
}

export interface RankQuery {
  indicator_id?: number;
  indicator_code?: string;
  period_year?: number;
  level?: RegionLevel;
  order?: 'asc' | 'desc';
  limit?: number;
  include_development_zones?: boolean;
}

export interface CompareQuery {
  indicator_id?: number;
  indicator_code?: string;
  region_codes?: string;
  region_ids?: string;
  period_year?: number;
}

export interface AdminDecisionPayload {
  role?: string;
  unit?: string;
  note?: string;
}

export interface RejectPayload {
  reason: string;
}

export interface AdminUserPatch {
  status?: 'active' | 'disabled';
  role?: string;
  note?: string;
}

export const api = {
  dashboard: {
    overview(periodYear = DEFAULT_PERIOD_YEAR): Promise<DashboardOverview> {
      return request<DashboardOverview>(
        `${API_PATHS.dashboardOverview}${buildQuery({ period_year: periodYear })}`
      );
    },
  },

  regions: {
    async list(query: RegionQuery = {}): Promise<PageResult<Region>> {
      const envelope = await requestWithMeta<Region[]>(
        `${API_PATHS.regions}${buildQuery({
          level: query.level,
          parent_id: query.parent_id,
          parent_code: query.parent_code,
          q: query.q,
          category: query.category,
          enabled: query.enabled === undefined ? true : query.enabled,
          page: query.page || 1,
          page_size: query.page_size || 20,
        })}`
      );
      return { items: envelope.data, meta: envelope.meta as PageMeta };
    },
    tree(rootCode = 'JD', depth = 2): Promise<RegionTree> {
      return request<RegionTree>(
        `${API_PATHS.regionTree}${buildQuery({ root_code: rootCode, depth })}`
      );
    },
    detail(regionId: number): Promise<RegionDetail> {
      return request<RegionDetail>(`${API_PATHS.regionDetail}/${regionId}`);
    },
    profile(regionId: number): Promise<RegionProfile> {
      return request<RegionProfile>(`${API_PATHS.regionProfile}/${regionId}/profile`);
    },
  },

  indicators: {
    async list(query: IndicatorQuery = {}): Promise<PageResult<Indicator>> {
      const envelope = await requestWithMeta<Indicator[]>(
        `${API_PATHS.indicators}${buildQuery({
          level: query.level,
          category: query.category,
          value_type: query.value_type,
          enabled: query.enabled === undefined ? true : query.enabled,
          page: query.page || 1,
          page_size: query.page_size || 50,
        })}`
      );
      return { items: envelope.data, meta: envelope.meta as PageMeta };
    },
    detail(indicatorId: number): Promise<Indicator> {
      return request<Indicator>(`${API_PATHS.indicators}/${indicatorId}`);
    },
  },

  dataValues: {
    async list(query: DataValueQuery = {}): Promise<PageResult<DataValue>> {
      const envelope = await requestWithMeta<DataValue[]>(
        `${API_PATHS.dataValues}${buildQuery({
          region_id: query.region_id,
          region_code: query.region_code,
          indicator_id: query.indicator_id,
          indicator_code: query.indicator_code,
          period_year: query.period_year || DEFAULT_PERIOD_YEAR,
          quality_status: query.quality_status,
          page: query.page || 1,
          page_size: query.page_size || 20,
        })}`
      );
      return { items: envelope.data, meta: envelope.meta as PageMeta };
    },
    rank(query: RankQuery): Promise<RankItem[]> {
      return request<RankItem[]>(
        `${API_PATHS.dataValuesRank}${buildQuery({
          indicator_id: query.indicator_id,
          indicator_code: query.indicator_code,
          period_year: query.period_year || DEFAULT_PERIOD_YEAR,
          level: query.level || 'town',
          order: query.order || 'desc',
          limit: query.limit || 10,
          include_development_zones: query.include_development_zones === true,
        })}`
      );
    },
    compare(query: CompareQuery): Promise<CompareItem[]> {
      return request<CompareItem[]>(
        `${API_PATHS.dataValuesCompare}${buildQuery({
          indicator_id: query.indicator_id,
          indicator_code: query.indicator_code,
          region_codes: query.region_codes,
          region_ids: query.region_ids,
          period_year: query.period_year || DEFAULT_PERIOD_YEAR,
        })}`
      );
    },
  },

  ai: {
    chat(payload: AIChatRequest): Promise<AIChatResponse> {
      return request<AIChatResponse>(API_PATHS.aiChat, {
        method: 'POST',
        data: payload,
        timeout: 60000,
      });
    },
    sessions(): Promise<unknown[]> {
      return request<unknown[]>(API_PATHS.aiSessions);
    },
  },

  auth: {
    me(): Promise<AuthUser> {
      return request<AuthUser>(API_PATHS.authMe);
    },
    login(username: string, password: string): Promise<LoginResponse> {
      return request<LoginResponse>(API_PATHS.authLogin, {
        method: 'POST',
        data: { username, password },
      });
    },
    apply(payload: ApplicationPayload): Promise<ApplicationSubmitResult> {
      return request<ApplicationSubmitResult>(API_PATHS.authApply, {
        method: 'POST',
        data: payload,
        showLoading: true,
      });
    },
    applicationStatus(applicationNo: string, statusToken: string): Promise<ApplicationStatusResponse> {
      return request<ApplicationStatusResponse>(
        `${API_PATHS.authApplicationStatus}${buildQuery({
          application_no: applicationNo,
          status_token: statusToken,
        })}`
      );
    },
    logout(): Promise<void> {
      return request<void>(API_PATHS.authLogout, { method: 'POST' });
    },
  },

  admin: {
    async applications(query: AdminApplicationQuery = {}): Promise<PageResult<AdminApplication>> {
      const envelope = await requestWithMeta<AdminApplication[]>(
        `${API_PATHS.adminApplications}${buildQuery({
          status: query.status,
          q: query.q,
          page: query.page || 1,
          page_size: query.page_size || 20,
        })}`
      );
      return { items: envelope.data, meta: envelope.meta as PageMeta };
    },
    approve(applicationId: number, payload: AdminDecisionPayload): Promise<unknown> {
      return request<unknown>(`${API_PATHS.adminApplications}/${applicationId}/approve`, {
        method: 'POST',
        data: payload,
        showLoading: true,
      });
    },
    reject(applicationId: number, payload: RejectPayload): Promise<unknown> {
      return request<unknown>(`${API_PATHS.adminApplications}/${applicationId}/reject`, {
        method: 'POST',
        data: payload,
        showLoading: true,
      });
    },
    async users(query: AdminUserQuery = {}): Promise<PageResult<AdminUser>> {
      const envelope = await requestWithMeta<AdminUser[]>(
        `${API_PATHS.adminUsers}${buildQuery({
          q: query.q,
          status: query.status,
          page: query.page || 1,
          page_size: query.page_size || 20,
        })}`
      );
      return { items: envelope.data, meta: envelope.meta as PageMeta };
    },
    updateUser(userId: number, patch: AdminUserPatch): Promise<AdminUser> {
      return request<AdminUser>(`${API_PATHS.adminUsers}/${userId}`, {
        method: 'PATCH',
        data: patch,
        showLoading: true,
      });
    },
    auditLogs(limit = 10): Promise<AuditLogItem[]> {
      return request<AuditLogItem[]>(
        `${API_PATHS.adminAuditLogs}${buildQuery({
          resource_type: 'application',
          limit,
        })}`
      );
    },
  },

  exports: {
    create(payload: ExportCreateRequest): Promise<ExportJob> {
      return request<ExportJob>(API_PATHS.exports, {
        method: 'POST',
        data: payload,
        showLoading: true,
      });
    },
    get(exportId: string): Promise<ExportJob> {
      return request<ExportJob>(`${API_PATHS.exports}/${exportId}`);
    },
    downloadUrl(exportId: string): string {
      return resolveApiUrl(`${API_PATHS.exports}/${exportId}/download`);
    },
  },
};

/** Convert legacy answer fields into renderable blocks. */
export function normalizeAnswerBlocks(response: AIChatResponse): AnswerBlock[] {
  if (response.blocks && response.blocks.length > 0) {
    return response.blocks;
  }
  const blocks: AnswerBlock[] = [];
  if (response.status === 'refused' || response.status === 'no_data') {
    blocks.push({
      type: 'notice',
      level: 'warning',
      title: response.status === 'refused' ? '无法回答' : '暂无数据',
      text:
        response.answer_markdown ||
        '当前数据没有覆盖该问题，请调整指标、区域或年份后重试。',
    });
  } else if (response.answer_markdown) {
    blocks.push({ type: 'summary', text: response.answer_markdown });
  }
  if (response.chart_spec) {
    blocks.push({
      type: 'chart',
      title: response.chart_spec.title,
      chart: response.chart_spec,
    });
  }
  if (response.citations && response.citations.length > 0) {
    blocks.push({
      type: 'source',
      title: '引用',
      citations: response.citations,
    });
  }
  if (blocks.length === 0) {
    blocks.push({
      type: 'notice',
      level: 'warning',
      text: '当前没有可展示的回答，请重试。',
    });
  }
  return blocks;
}

/**
 * Clearly labelled fallback used only when the AI endpoint is not available.
 * Numbers are placeholders for component/layout verification, never presented
 * as real statistics.
 */
export function buildDemoAnswer(question: string): AIChatResponse {
  const chart: ChartSpec = {
    version: '1.0',
    type: 'hbar',
    title: '演示图表（占位数据）',
    unit: '亿元',
    categories: ['示例镇街甲', '示例镇街乙', '示例镇街丙'],
    series: [{ name: '演示数值', values: [12.4, 9.8, 7.2] }],
    options: { show_values: true, sort: 'desc', max_items: 5 },
  };
  return {
    session_id: null,
    message_id: null,
    status: 'done',
    demo: true,
    answer_markdown: `关于“${question}”，AI 服务当前不可用。以下内容用于展示答案结构与组件样式，数字均为占位示例，不作为决策依据。`,
    blocks: [
      {
        type: 'notice',
        level: 'warning',
        title: '演示回答',
        text: 'AI 接口尚未接入或请求失败。本回答不包含真实统计结论，正式环境将以服务端 ChartSpec 与引用为准。',
      },
      {
        type: 'metric_grid',
        title: '指标示例',
        metrics: [
          { label: '演示指标一', value: 12.4, unit: '亿元', year: 2025, quality_status: 'estimated' },
          { label: '演示指标二', value: 9.8, unit: '万人', year: 2025, quality_status: 'estimated' },
          { label: '演示指标三', value: 7.2, unit: '个', year: 2025, quality_status: 'estimated' },
        ],
      },
      { type: 'chart', title: chart.title, chart },
      {
        type: 'table',
        title: '数据表示例',
        columns: ['区域', '演示值（亿元）'],
        rows: [
          ['示例镇街甲', 12.4],
          ['示例镇街乙', 9.8],
          ['示例镇街丙', 7.2],
        ],
      },
      {
        type: 'ranking',
        title: '排名示例',
        ranking: [
          { rank: 1, name: '示例镇街甲', value: 12.4, unit: '亿元' },
          { rank: 2, name: '示例镇街乙', value: 9.8, unit: '亿元' },
          { rank: 3, name: '示例镇街丙', value: 7.2, unit: '亿元' },
        ],
      },
      {
        type: 'source',
        title: '引用与来源',
        text: '演示结构数据，非真实统计。正式环境将展示指标、区域、年份、来源与数据时点。',
        citations: [
          { indicator: '演示指标', period: '2025', region_level: '演示', source: 'demo' },
        ],
      },
      {
        type: 'actions',
        title: '下一步',
        actions: [
          { key: 'regions', label: '查看区域数据', type: 'navigate', url: '/pages/regions/regions' },
          { key: 'apply', label: '申请账号后导出', type: 'apply' },
        ],
      },
    ],
    citations: [
      { indicator: '演示指标', period: '2025', region_level: '演示', source: 'demo' },
    ],
    follow_up_questions: [
      '2025 年各镇街常住人口排名如何？',
      '揭东区今年的地区生产总值是多少？',
    ],
  };
}

/** Basic export title sanitation shared by the export page. */
export function sanitizeExportTitle(title: string): string {
  return title.replace(/[\\/:*?"<>|]/g, ' ').replace(/\s+/g, ' ').trim().slice(0, 60);
}

export { formatDate };
