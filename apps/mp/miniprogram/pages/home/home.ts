import { api } from '../../services/api';
import { DEFAULT_PERIOD_YEAR } from '../../services/config';
import {
  isAuthError,
  toErrorMessage,
  toErrorRequestId,
} from '../../services/request';
import type { DashboardMetric, DashboardOverview, Region } from '../../types/api';
import type { IdentityView, MetricCardModel } from '../../types/models';
import {
  canAccessData,
  getIdentity,
  guestQuotaText,
} from '../../utils/auth';
import { formatDateTime, formatNumber } from '../../utils/format';
import { setStorage, STORAGE_KEYS } from '../../utils/storage';

interface CoreMetricConfig {
  code: string;
  label: string;
  unit: string;
  precision: number;
}

const CORE_METRICS: CoreMetricConfig[] = [
  { code: 'area', label: '区域面积', unit: '平方公里', precision: 2 },
  { code: 'population_resident', label: '常住人口', unit: '人', precision: 0 },
  { code: 'gdp', label: '地区生产总值', unit: '亿元', precision: 2 },
  { code: 'budget_revenue', label: '地方一般公共预算收入', unit: '亿元', precision: 2 },
];

Page({
  data: {
    loading: true,
    error: '',
    requestId: '',
    identity: null as IdentityView | null,
    locked: false,
    periodYear: DEFAULT_PERIOD_YEAR,
    districtId: 0,
    districtCode: 'JD',
    districtName: '揭东区',
    dataAsOfLabel: '',
    coverageText: '',
    demoMode: true,
    metrics: [] as MetricCardModel[],
    towns: [] as Region[],
    townTotal: 0,
    guestQuota: '',
    skeletons: [1, 2, 3, 4],
  },

  onLoad() {
    const identity = getIdentity();
    this.setData({
      identity,
      locked: !canAccessData(),
      guestQuota: guestQuotaText(),
    });
    if (canAccessData()) {
      this.load();
    } else {
      this.setData({ loading: false });
    }
  },

  onShow() {
    const identity = getIdentity();
    const locked = !canAccessData();
    const wasLocked = this.data.locked;
    this.setData({
      identity,
      locked,
      guestQuota: guestQuotaText(),
    });
    if (locked && !wasLocked) {
      this.setData({ loading: false, metrics: [], towns: [] });
    } else if (!locked && wasLocked) {
      this.load();
    }
  },

  async load() {
    if (!canAccessData()) {
      this.setData({ loading: false, locked: true });
      return;
    }
    this.setData({ loading: true, error: '', requestId: '' });
    try {
      const [overview, towns, districts] = await Promise.all([
        api.dashboard.overview(DEFAULT_PERIOD_YEAR),
        api.regions.list({ level: 'town', page: 1, page_size: 5 }),
        api.regions.list({ level: 'district', page: 1, page_size: 1 }),
      ]);
      const district = districts.items.length ? districts.items[0] : null;
      this.setData({
        loading: false,
        districtId: district ? district.id : this.data.districtId,
        districtCode: district ? district.code : this.data.districtCode,
        districtName: district ? district.name : this.data.districtName,
        periodYear: overview.period_year,
        metrics: this.buildMetrics(overview),
        towns: towns.items,
        townTotal: overview.town_count || towns.meta.total,
        dataAsOfLabel: overview.data_as_of
          ? formatDateTime(overview.data_as_of)
          : '演示种子数据',
        coverageText:
          overview.coverage === null ? '' : `${formatNumber(overview.coverage, 1)}%`,
      });
    } catch (error) {
      if (isAuthError(error)) {
        this.setData({ identity: getIdentity(), locked: !canAccessData() });
      }
      this.setData({
        loading: false,
        error: toErrorMessage(error),
        requestId: toErrorRequestId(error),
      });
    }
  },

  buildMetrics(overview: DashboardOverview): MetricCardModel[] {
    const lookup: Record<string, DashboardMetric> = {};
    overview.metrics.forEach((metric) => {
      lookup[metric.code] = metric;
    });
    return CORE_METRICS.map((config) => {
      const source = lookup[config.code];
      return {
        code: config.code,
        label: source ? source.label : config.label,
        value: source ? source.value_number : null,
        unit: source ? source.unit : config.unit,
        year: overview.period_year,
        status: source ? source.quality_status : 'missing',
        precision: config.precision,
      };
    });
  },

  handleMetricTap(event: WechatMiniprogram.CustomEvent<{ code: string }>) {
    const code = event.detail.code;
    if (!code) {
      return;
    }
    if (!this.data.districtId) {
      wx.showToast({ title: '区域信息尚未加载', icon: 'none' });
      return;
    }
    wx.navigateTo({
      url:
        `/pages/indicator-detail/indicator-detail?region_id=${this.data.districtId}` +
        `&region_code=${encodeURIComponent(this.data.districtCode)}` +
        `&indicator_code=${encodeURIComponent(code)}` +
        `&period_year=${this.data.periodYear}`,
    });
  },

  handleTownTap(event: WechatMiniprogram.TouchEvent) {
    const dataset = event.currentTarget.dataset;
    const id = Number(dataset.id);
    const name = typeof dataset.name === 'string' ? dataset.name : '';
    if (!id) {
      return;
    }
    wx.navigateTo({
      url:
        `/pages/region-detail/region-detail?id=${id}` +
        `&name=${encodeURIComponent(name)}`,
    });
  },

  goRegions() {
    setStorage(STORAGE_KEYS.preferredRegionLevel, 'town');
    wx.switchTab({ url: '/pages/regions/regions' });
  },

  goAi() {
    wx.switchTab({ url: '/pages/ai/ai' });
  },

  goApply() {
    wx.navigateTo({ url: '/pages/apply/apply' });
  },

  goExport() {
    if (!this.data.identity || !this.data.identity.canExport) {
      wx.showModal({
        title: '需要账号',
        content: '导出功能仅对已批准账号开放，游客可先提交申请。',
        confirmText: '去申请',
        cancelText: '取消',
        success: (result) => {
          if (result.confirm) {
            this.goApply();
          }
        },
      });
      return;
    }
    wx.navigateTo({
      url:
        `/pages/export/export?region_id=${this.data.districtId}` +
        `&region_name=${encodeURIComponent(this.data.districtName)}` +
        `&period_year=${this.data.periodYear}`,
    });
  },

  onRetry() {
    this.load();
  },
});
