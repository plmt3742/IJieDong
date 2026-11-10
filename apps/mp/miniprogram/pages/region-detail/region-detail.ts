import { api } from '../../services/api';
import { DEMO_SOURCE_LABEL } from '../../services/config';
import {
  isAuthError,
  toErrorMessage,
  toErrorRequestId,
} from '../../services/request';
import type { ProfileMetric, RegionProfile } from '../../types/api';
import type { IdentityView } from '../../types/models';
import { canAccessData, canExport, getIdentity } from '../../utils/auth';
import {
  formatDateTime,
  levelLabel,
  precisionForCode,
  qualityLabel,
} from '../../utils/format';
import { setStorage, STORAGE_KEYS } from '../../utils/storage';

type MetricView = ProfileMetric & { precision: number; qualityText: string };

Page({
  data: {
    loading: true,
    error: '',
    requestId: '',
    locked: false,
    identity: null as IdentityView | null,
    regionId: 0,
    regionName: '',
    regionLevel: '',
    regionLevelLabel: '',
    regionCategory: '',
    parentId: null as number | null,
    parentName: '',
    intro: '',
    feature: '',
    introExpanded: false,
    featureExpanded: false,
    hasMoreIntro: false,
    hasMoreFeature: false,
    metricViews: [] as MetricView[],
    dataAsOfLabel: '',
    exportAllowed: false,
    sourceLabel: DEMO_SOURCE_LABEL,
    skeletons: [1, 2, 3, 4],
  },

  onLoad(query: Record<string, string | undefined>) {
    const regionId = Number(query.id);
    const regionName = query.name ? safeDecode(query.name) : '';
    const identity = getIdentity();
    const locked = !canAccessData();
    this.setData({
      regionId,
      regionName,
      identity,
      locked,
      exportAllowed: canExport(),
    });
    if (regionName) {
      wx.setNavigationBarTitle({ title: regionName });
    }
    if (!regionId) {
      this.setData({ loading: false, error: '缺少区域参数。', requestId: '' });
      return;
    }
    if (locked) {
      this.setData({ loading: false });
      return;
    }
    this.load();
  },

  onShow() {
    const identity = getIdentity();
    const locked = !canAccessData();
    if (locked !== this.data.locked) {
      this.setData({ identity, locked, exportAllowed: canExport() });
    }
  },

  async load() {
    if (!canAccessData()) {
      this.setData({ loading: false, locked: true });
      return;
    }
    this.setData({ loading: true, error: '', requestId: '' });
    try {
      const profile = await api.regions.profile(this.data.regionId);
      this.applyProfile(profile);
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

  applyProfile(profile: RegionProfile) {
    const intro = profile.intro || '';
    const feature = profile.feature || '';
    const metricViews: MetricView[] = profile.metrics.map((metric) => ({
      ...metric,
      precision: precisionForCode(metric.code),
      qualityText: qualityLabel(metric.quality_status),
    }));
    this.setData({
      loading: false,
      regionId: profile.region.id,
      regionName: profile.region.name,
      regionLevel: profile.region.level,
      regionLevelLabel: levelLabel(profile.region.level),
      regionCategory: profile.region.category,
      parentId: profile.parent ? profile.parent.id : null,
      parentName: profile.parent ? profile.parent.name : '',
      intro,
      feature,
      hasMoreIntro: intro.length > 96 || intro.split('\n').length > 3,
      hasMoreFeature: feature.length > 96 || feature.split('\n').length > 3,
      metricViews,
      dataAsOfLabel: profile.data_as_of
        ? formatDateTime(profile.data_as_of)
        : '演示种子数据',
      exportAllowed: canExport(),
    });
    wx.setNavigationBarTitle({ title: profile.region.name });
  },

  toggleIntro() {
    this.setData({ introExpanded: !this.data.introExpanded });
  },

  toggleFeature() {
    this.setData({ featureExpanded: !this.data.featureExpanded });
  },

  handleMetricTap(event: WechatMiniprogram.CustomEvent<{ code: string }>) {
    const code = event.detail.code;
    const metric = this.data.metricViews.find((item) => item.code === code);
    if (!metric) {
      return;
    }
    wx.navigateTo({
      url:
        `/pages/indicator-detail/indicator-detail?region_id=${this.data.regionId}` +
        `&indicator_id=${metric.indicator_id}` +
        `&indicator_code=${encodeURIComponent(metric.code)}` +
        `&period_year=${metric.period_year}`,
    });
  },

  handleExport() {
    if (!this.data.exportAllowed) {
      wx.showModal({
        title: '需要账号',
        content: '导出功能仅对已批准账号开放，游客可先提交申请。',
        confirmText: '去申请',
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
        `/pages/export/export?region_id=${this.data.regionId}` +
        `&region_name=${encodeURIComponent(this.data.regionName)}` +
        `&period_year=2025`,
    });
  },

  goParent() {
    if (!this.data.parentId) {
      return;
    }
    wx.navigateTo({
      url:
        `/pages/region-detail/region-detail?id=${this.data.parentId}` +
        `&name=${encodeURIComponent(this.data.parentName)}`,
    });
  },

  goRegions() {
    setStorage(STORAGE_KEYS.preferredRegionLevel, this.data.regionLevel || 'town');
    wx.switchTab({ url: '/pages/regions/regions' });
  },

  goApply() {
    wx.navigateTo({ url: '/pages/apply/apply' });
  },

  onRetry() {
    this.load();
  },
});

function safeDecode(value: string): string {
  try {
    return decodeURIComponent(value);
  } catch (error) {
    return value;
  }
}
