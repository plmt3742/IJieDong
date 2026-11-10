import { api } from '../../services/api';
import {
  isAuthError,
  toErrorMessage,
  toErrorRequestId,
} from '../../services/request';
import type { Region, RegionLevel } from '../../types/api';
import type { IdentityView } from '../../types/models';
import { canAccessData, getIdentity } from '../../utils/auth';
import { getStorage, removeStorage, STORAGE_KEYS } from '../../utils/storage';

const PAGE_SIZE = 20;

Page({
  data: {
    level: 'district' as RegionLevel,
    tabs: [
      { key: 'district', label: '区' },
      { key: 'town', label: '镇街' },
      { key: 'village', label: '村居' },
    ],
    identity: null as IdentityView | null,
    locked: false,
    state: 'loading' as string,
    items: [] as Region[],
    towns: [] as Region[],
    page: 1,
    total: 0,
    hasNext: false,
    q: '',
    emptyText: '',
    error: '',
    requestId: '',
    loading: false,
    showVillagePicker: false,
    villageParent: null as Region | null,
    skeletons: [1, 2, 3, 4],
  },

  onLoad(query: Record<string, string | undefined>) {
    const identity = getIdentity();
    const locked = !canAccessData();
    const preferred = getStorage<string>(STORAGE_KEYS.preferredRegionLevel, '');
    removeStorage(STORAGE_KEYS.preferredRegionLevel);
    const queryLevel = query.level === 'district' || query.level === 'town' || query.level === 'village'
      ? (query.level as RegionLevel)
      : null;
    const level: RegionLevel =
      queryLevel ||
      (preferred === 'district' || preferred === 'town' || preferred === 'village'
        ? (preferred as RegionLevel)
        : 'district');
    this.setData({
      identity,
      locked,
      level,
      state: locked ? 'locked' : 'loading',
      showVillagePicker: level === 'village',
    });
    if (!locked) {
      this.load(true);
    }
  },

  onShow() {
    const locked = !canAccessData();
    if (locked !== this.data.locked) {
      this.setData({ locked, identity: getIdentity(), state: locked ? 'locked' : this.data.state });
      if (!locked) {
        this.load(true);
      }
    }
  },

  async load(reset: boolean) {
    if (!canAccessData()) {
      this.setData({ locked: true, state: 'locked', loading: false });
      return;
    }
    if (this.data.level === 'village' && !this.data.villageParent) {
      await this.loadTowns();
      return;
    }
    if (
      this.data.level === 'village' &&
      this.data.villageParent &&
      this.data.villageParent.category === 'development_zone'
    ) {
      this.setData({
        loading: false,
        state: 'empty',
        items: [],
        emptyText: '该区域为开发区/生态城，不设村居。',
      });
      return;
    }

    const nextPage = reset ? 1 : this.data.page + 1;
    this.setData({
      loading: true,
      error: '',
      requestId: '',
      state: reset ? 'loading' : this.data.state,
    });
    try {
      const result = await api.regions.list({
        level: this.data.level,
        parent_id:
          this.data.level === 'village' && this.data.villageParent
            ? this.data.villageParent.id
            : undefined,
        q: this.data.q || undefined,
        page: nextPage,
        page_size: PAGE_SIZE,
      });
      const items = reset ? result.items : this.data.items.concat(result.items);
      this.setData({
        loading: false,
        items,
        page: result.meta.page,
        total: result.meta.total,
        hasNext: result.meta.has_next,
        state: items.length ? 'ready' : 'empty',
        emptyText: this.buildEmptyText(),
      });
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

  async loadTowns() {
    this.setData({ loading: true, error: '', requestId: '', state: 'loading' });
    try {
      const result = await api.regions.list({ level: 'town', page: 1, page_size: 50 });
      this.setData({
        loading: false,
        towns: result.items,
        items: [],
        page: 1,
        total: 0,
        hasNext: false,
        state: 'ready',
        showVillagePicker: true,
      });
    } catch (error) {
      this.setData({
        loading: false,
        state: 'error',
        error: toErrorMessage(error),
        requestId: toErrorRequestId(error),
      });
    }
  },

  buildEmptyText(): string {
    if (this.data.q) {
      return `没有找到“${this.data.q}”相关结果，可清空关键词后重试。`;
    }
    if (this.data.level === 'village') {
      return '该镇街暂无村居数据。';
    }
    return '当前没有可展示的区域数据。';
  },

  switchTab(event: WechatMiniprogram.TouchEvent) {
    const level = event.currentTarget.dataset.level as RegionLevel;
    if (!level || level === this.data.level) {
      return;
    }
    this.setData(
      {
        level,
        q: '',
        items: [],
        towns: [],
        page: 1,
        total: 0,
        hasNext: false,
        villageParent: null,
        showVillagePicker: level === 'village',
        state: 'loading',
        error: '',
        requestId: '',
      },
      () => {
        this.load(true);
      }
    );
  },

  handleSearchInput(event: WechatMiniprogram.Input) {
    this.setData({ q: event.detail.value });
  },

  handleSearchConfirm() {
    this.load(true);
  },

  clearSearch() {
    this.setData({ q: '' }, () => {
      this.load(true);
    });
  },

  handleRowTap(event: WechatMiniprogram.TouchEvent) {
    const dataset = event.currentTarget.dataset;
    const index = Number(dataset.index);
    if (this.data.level === 'village' && !this.data.villageParent) {
      this.selectTown(index);
      return;
    }
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

  selectTown(index: number) {
    const town = this.data.towns[index];
    if (!town) {
      return;
    }
    if (town.category === 'development_zone') {
      this.setData({
        villageParent: town,
        showVillagePicker: false,
        items: [],
        total: 0,
        hasNext: false,
        state: 'empty',
        emptyText: '该区域为开发区/生态城，不设村居。',
      });
      return;
    }
    this.setData(
      {
        villageParent: town,
        showVillagePicker: false,
        items: [],
        page: 1,
        total: 0,
        hasNext: false,
        state: 'loading',
      },
      () => {
        this.load(true);
      }
    );
  },

  changeVillageParent() {
    this.setData(
      {
        villageParent: null,
        showVillagePicker: true,
        items: [],
        total: 0,
        hasNext: false,
        q: '',
      },
      () => {
        this.loadTowns();
      }
    );
  },

  goApply() {
    wx.navigateTo({ url: '/pages/apply/apply' });
  },

  onReachBottom() {
    if (this.data.hasNext && !this.data.loading && this.data.state === 'ready') {
      this.load(false);
    }
  },

  onRetry() {
    this.load(true);
  },
});
