import { api } from '../../services/api';
import { DEFAULT_PERIOD_YEAR, DEMO_SOURCE_LABEL } from '../../services/config';
import {
  isAuthError,
  isFeatureUnavailable,
  toErrorMessage,
  toErrorRequestId,
} from '../../services/request';
import type {
  CompareItem,
  DataValue,
  Indicator,
  RegionDetail,
  RegionLevel,
  RankItem,
} from '../../types/api';
import type { ChartSpec } from '../../types/chart';
import type { IdentityView } from '../../types/models';
import { canAccessData, canExport, getIdentity } from '../../utils/auth';
import {
  formatDateTime,
  formatNumber,
  formatWithUnit,
  levelLabel,
  precisionForCode,
  qualityLabel,
  qualityTone as toneOf,
} from '../../utils/format';
import { setStorage, STORAGE_KEYS } from '../../utils/storage';

interface CompareRow {
  id: number;
  name: string;
  value: string;
  diff: string;
}

Page({
  data: {
    loading: true,
    error: '',
    requestId: '',
    locked: false,
    identity: null as IdentityView | null,
    state: 'loading' as string,
    regionId: 0,
    regionName: '',
    regionLevel: '' as RegionLevel | '',
    regionLevelLabel: '',
    regionCategory: '',
    parentId: null as number | null,
    indicatorId: 0,
    indicatorCode: '',
    indicatorName: '',
    indicatorUnit: '',
    indicatorPrecision: 0,
    valueType: '',
    periodYear: DEFAULT_PERIOD_YEAR,
    valueDisplay: '',
    textValue: '',
    isText: false,
    qualityText: '',
    qualityToneName: 'muted',
    sourceLabel: DEMO_SOURCE_LABEL,
    updatedAtLabel: '',
    rankChart: null as ChartSpec | null,
    rankNote: '',
    rankItems: [] as RankItem[],
    compareChart: null as ChartSpec | null,
    compareRows: [] as CompareRow[],
    compareNote: '',
    compareLoading: false,
    compareLoaded: false,
    canCompare: false,
    exportAllowed: false,
    skeletons: [1, 2, 3, 4],
  },

  onLoad(query: Record<string, string | undefined>) {
    const regionId = Number(query.region_id);
    const indicatorId = Number(query.indicator_id);
    const indicatorCode = query.indicator_code || '';
    const periodYear = Number(query.period_year) || DEFAULT_PERIOD_YEAR;
    const identity = getIdentity();
    const locked = !canAccessData();
    this.setData({
      regionId,
      indicatorId,
      indicatorCode,
      periodYear,
      identity,
      locked,
      exportAllowed: canExport(),
    });
    if (!regionId || (!indicatorId && !indicatorCode)) {
      this.setData({ loading: false, state: 'error', error: '缺少区域或指标参数。' });
      return;
    }
    if (locked) {
      this.setData({ loading: false, state: 'locked' });
      return;
    }
    this.load();
  },

  onShow() {
    const locked = !canAccessData();
    if (locked !== this.data.locked) {
      this.setData({
        locked,
        identity: getIdentity(),
        state: locked ? 'locked' : this.data.state,
        exportAllowed: canExport(),
      });
    }
  },

  async load() {
    if (!canAccessData()) {
      this.setData({ loading: false, state: 'locked' });
      return;
    }
    this.setData({ loading: true, state: 'loading', error: '', requestId: '' });
    try {
      const region = await api.regions.detail(this.data.regionId);
      const indicator = await this.resolveIndicator();
      if (!indicator) {
        this.setData({
          loading: false,
          state: 'empty',
          regionName: region.name,
          regionLevel: region.level,
          regionLevelLabel: levelLabel(region.level),
          error: '',
        });
        return;
      }
      this.setData({
        regionName: region.name,
        regionLevel: region.level,
        regionLevelLabel: levelLabel(region.level),
        regionCategory: region.category,
        parentId: region.parent_id,
        indicatorId: indicator.id,
        indicatorCode: indicator.code,
        indicatorName: indicator.name,
        indicatorUnit: indicator.unit,
        indicatorPrecision: indicator.precision,
        valueType: indicator.value_type,
        exportAllowed: canExport(),
      });
      wx.setNavigationBarTitle({ title: indicator.name });

      if (!isApplicable(indicator, region)) {
        this.setData({ loading: false, state: 'not-applicable' });
        return;
      }

      const result = await api.dataValues.list({
        region_id: region.id,
        indicator_id: indicator.id,
        indicator_code: indicator.code,
        period_year: this.data.periodYear,
        page_size: 10,
      });
      if (!result.items.length) {
        this.setData({ loading: false, state: 'empty' });
        return;
      }
      const value = result.items[0];
      this.applyValue(value, indicator, region);
    } catch (error) {
      if (isAuthError(error)) {
        this.setData({ identity: getIdentity(), locked: !canAccessData() });
      }
      this.setData({
        loading: false,
        state: 'error',
        error: toErrorMessage(error),
        requestId: toErrorRequestId(error),
      });
    }
  },

  async resolveIndicator(): Promise<Indicator | null> {
    if (this.data.indicatorId) {
      try {
        return await api.indicators.detail(this.data.indicatorId);
      } catch (error) {
        if (!isFeatureUnavailable(error)) {
          throw error;
        }
      }
    }
    if (!this.data.indicatorCode) {
      return null;
    }
    const result = await api.indicators.list({ page_size: 100 });
    return result.items.find((item) => item.code === this.data.indicatorCode) || null;
  },

  applyValue(value: DataValue, indicator: Indicator, region: RegionDetail) {
    const isText = indicator.value_type === 'long_text' || !!value.value_text;
    const precision = indicator.precision === null ? precisionForCode(indicator.code) : indicator.precision;
    const notApplicable = value.quality_status === 'not_applicable';
    this.setData({
      loading: false,
      state: 'ready',
      isText,
      textValue: value.value_text || '',
      valueDisplay: isText
        ? ''
        : notApplicable
          ? '不适用'
          : formatNumber(value.value_number, precision),
      indicatorPrecision: precision,
      qualityText: qualityLabel(value.quality_status),
      qualityToneName: toneOf(value.quality_status),
      updatedAtLabel: formatDateTime(value.updated_at),
      sourceLabel: DEMO_SOURCE_LABEL,
      canCompare: !isText && region.level !== 'district' && !!region.parent_id,
      exportAllowed: canExport(),
    });
    if (!isText) {
      this.loadRank(indicator);
    }
  },

  async loadRank(indicator: Indicator) {
    if (!indicator.applicable_levels.includes('town')) {
      this.setData({ rankNote: '该指标不适用镇街排名，仅展示当前值。' });
      return;
    }
    try {
      const items = await api.dataValues.rank({
        indicator_id: indicator.id,
        indicator_code: indicator.code,
        period_year: this.data.periodYear,
        level: 'town',
        order: 'desc',
        limit: 8,
      });
      if (!items.length) {
        this.setData({ rankNote: '当前没有可用于排名的数据。' });
        return;
      }
      const chart: ChartSpec = {
        version: '1.0',
        type: 'hbar',
        title: `${this.data.periodYear} 年${indicator.name}镇街排名`,
        unit: indicator.unit,
        categories: items.map((item) => item.region_name),
        series: [{ name: indicator.name, values: items.map((item) => item.value_number) }],
        options: { show_values: true, max_items: 8 },
      };
      this.setData({ rankItems: items, rankChart: chart, rankNote: '' });
    } catch (error) {
      this.setData({
        rankNote: isFeatureUnavailable(error)
          ? '排名接口尚未就绪，暂不展示图表。'
          : toErrorMessage(error),
      });
    }
  },

  async loadCompare() {
    if (!this.data.canCompare || !this.data.parentId) {
      wx.showToast({ title: '当前区域暂不支持对比', icon: 'none' });
      return;
    }
    if (this.data.compareLoading) {
      return;
    }
    this.setData({ compareLoading: true, compareNote: '' });
    try {
      const siblings = await api.regions.list({
        level: this.data.regionLevel as RegionLevel,
        parent_id: this.data.parentId,
        page_size: 10,
      });
      const otherCodes = siblings.items
        .filter((item) => item.id !== this.data.regionId)
        .slice(0, 3)
        .map((item) => item.code);
      const current = this.data.regionId;
      const detail = await api.regions.detail(current);
      const codes = [detail.code].concat(otherCodes);
      if (codes.length < 2) {
        this.setData({
          compareLoading: false,
          compareNote: '同一上级区域下没有其他可比区域。',
        });
        return;
      }
      const items: CompareItem[] = await api.dataValues.compare({
        indicator_id: this.data.indicatorId,
        indicator_code: this.data.indicatorCode,
        region_codes: codes.join(','),
        period_year: this.data.periodYear,
      });
      if (items.length < 2) {
        this.setData({
          compareLoading: false,
          compareNote: '可比区域数据不足，暂不展示对比图表。',
        });
        return;
      }
      const precision = this.data.indicatorPrecision;
      const rows: CompareRow[] = items.map((item) => ({
        id: item.region_id,
        name: item.region_name,
        value: formatWithUnit(item.value_number, item.unit, precision),
        diff:
          item.diff_from_first === null
            ? ''
            : `${item.diff_from_first > 0 ? '+' : ''}${formatNumber(item.diff_from_first, precision)}`,
      }));
      const chart: ChartSpec = {
        version: '1.0',
        type: 'bar',
        title: `${this.data.periodYear} 年${this.data.indicatorName}区域对比`,
        unit: this.data.indicatorUnit,
        categories: items.map((item) => item.region_name),
        series: [
          {
            name: this.data.indicatorName,
            values: items.map((item) => item.value_number),
          },
        ],
        options: { show_values: true },
      };
      this.setData({
        compareLoading: false,
        compareLoaded: true,
        compareRows: rows,
        compareChart: chart,
        compareNote: '',
      });
    } catch (error) {
      this.setData({
        compareLoading: false,
        compareNote: isFeatureUnavailable(error)
          ? '对比接口尚未就绪，暂时无法展示。'
          : toErrorMessage(error),
      });
    }
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
        `&indicator_id=${this.data.indicatorId}` +
        `&indicator_code=${encodeURIComponent(this.data.indicatorCode)}` +
        `&indicator_name=${encodeURIComponent(this.data.indicatorName)}` +
        `&unit=${encodeURIComponent(this.data.indicatorUnit)}` +
        `&period_year=${this.data.periodYear}`,
    });
  },

  handleAskAi() {
    const question = `请说明${this.data.periodYear} 年${this.data.regionName}的${this.data.indicatorName}情况，并给出数据来源。`;
    wx.navigateTo({
      url: `/pages/chat/chat?question=${encodeURIComponent(question)}`,
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

function isApplicable(indicator: Indicator, region: RegionDetail): boolean {
  if (!indicator.applicable_levels.includes(region.level)) {
    return false;
  }
  const categories = indicator.applicable_region_categories;
  if (categories && categories.length && !categories.includes(region.category)) {
    return false;
  }
  return true;
}
