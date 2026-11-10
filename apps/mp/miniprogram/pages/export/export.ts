import { api } from '../../services/api';
import {
  DEFAULT_PERIOD_YEAR,
  DEMO_SOURCE_LABEL,
  WATERMARK_TEXT,
  resolveApiUrl,
} from '../../services/config';
import {
  isFeatureUnavailable,
  toErrorMessage,
} from '../../services/request';
import type {
  ExportFormat,
  ExportJob,
} from '../../types/api';
import type { ExportFormatOption, IdentityView } from '../../types/models';
import { canExport, getIdentity, getToken } from '../../utils/auth';
import {
  formatBytes,
  formatDateTime,
} from '../../utils/format';

interface FormatOption extends ExportFormatOption {
  extension: string;
}

Page({
  data: {
    identity: null as IdentityView | null,
    allowed: false,
    locked: false,
    state: 'idle' as string,
    formats: [] as FormatOption[],
    selectedFormat: '',
    title: '',
    regionId: 0,
    regionName: '',
    indicatorId: 0,
    indicatorCode: '',
    indicatorName: '',
    unit: '',
    periodYear: DEFAULT_PERIOD_YEAR,
    dataAsOfLabel: '演示种子数据',
    generatedAtLabel: '',
    expiresAtLabel: '',
    sourceLabel: DEMO_SOURCE_LABEL,
    watermark: WATERMARK_TEXT,
    job: null as ExportJob | null,
    progress: 0,
    pollTimerId: 0,
    pollCount: 0,
    error: '',
    fileSizeLabel: '',
  },

  onLoad(query: Record<string, string | undefined>) {
    const identity = getIdentity();
    const allowed = canExport();
    const locked = identity.isApplicant;
    const regionId = Number(query.region_id);
    const regionName = query.region_name ? safeDecode(query.region_name) : '揭东区';
    const indicatorId = Number(query.indicator_id);
    const indicatorCode = query.indicator_code || '';
    const indicatorName = query.indicator_name ? safeDecode(query.indicator_name) : '';
    const unit = query.unit ? safeDecode(query.unit) : '';
    const periodYear = Number(query.period_year) || DEFAULT_PERIOD_YEAR;
    const title = sanitizeTitle(
      indicatorName
        ? `${periodYear} 年${regionName}${indicatorName}`
        : `${periodYear} 年${regionName}区域汇报卡`
    );
    this.setData({
      identity,
      allowed,
      locked,
      regionId,
      regionName,
      indicatorId,
      indicatorCode,
      indicatorName,
      unit,
      periodYear,
      title,
      generatedAtLabel: formatDateTime(new Date().toISOString()),
      formats: buildFormats(),
    });
    wx.setNavigationBarTitle({ title: '导出' });
    if (allowed) {
      this.loadDataAsOf();
    }
  },

  async loadDataAsOf() {
    try {
      const overview = await api.dashboard.overview(this.data.periodYear);
      this.setData({
        dataAsOfLabel: overview.data_as_of
          ? formatDateTime(overview.data_as_of)
          : '演示种子数据',
      });
    } catch (error) {
      this.setData({ dataAsOfLabel: '演示种子数据' });
    }
  },

  selectFormat(event: WechatMiniprogram.TouchEvent) {
    const key = event.currentTarget.dataset.key as ExportFormat;
    const format = this.data.formats.find((item) => item.key === key);
    if (!format || format.disabled) {
      return;
    }
    if (!this.data.allowed) {
      wx.showToast({ title: '请先申请账号', icon: 'none' });
      return;
    }
    this.setData({
      selectedFormat: key,
      state: 'idle',
      job: null,
      progress: 0,
      error: '',
      fileSizeLabel: '',
    });
  },

  async handleGenerate() {
    if (!this.data.allowed) {
      this.goApply();
      return;
    }
    if (!this.data.selectedFormat) {
      wx.showToast({ title: '请先选择导出格式', icon: 'none' });
      return;
    }
    if (this.data.state === 'generating') {
      return;
    }
    this.setData({
      state: 'generating',
      progress: 0,
      job: null,
      error: '',
      pollCount: 0,
      fileSizeLabel: '',
      generatedAtLabel: formatDateTime(new Date().toISOString()),
      expiresAtLabel: '',
    });
    try {
      const job = await api.exports.create({
        source_type: 'report',
        source_id: `report_${this.data.regionId}_${this.data.indicatorId || 'all'}_${this.data.periodYear}`,
        format: this.data.selectedFormat as ExportFormat,
        title: this.data.title,
        options: {
          orientation: 'portrait',
          include_citations: true,
          watermark: true,
          max_rows: 100,
        },
        source: {
          region_id: this.data.regionId,
          region_name: this.data.regionName,
          indicator_id: this.data.indicatorId || undefined,
          indicator_code: this.data.indicatorCode || undefined,
          indicator_name: this.data.indicatorName || undefined,
          period_year: this.data.periodYear,
          unit: this.data.unit || undefined,
        },
      });
      this.setData({
        job,
        progress: typeof job.progress === 'number' ? job.progress : 0,
      });
      if (job.status === 'ready') {
        this.markReady(job);
        return;
      }
      if (job.status === 'failed' || job.status === 'expired') {
        this.setData({ state: 'failed', error: job.error ? '导出任务失败。' : '导出失败。' });
        return;
      }
      this.pollExport(job.export_id, 0);
    } catch (error) {
      if (isFeatureUnavailable(error)) {
        this.setData({
          state: 'failed',
          error: '导出接口尚未就绪（契约待补），未生成空文件。',
        });
        return;
      }
      this.setData({ state: 'failed', error: toErrorMessage(error) });
    }
  },

  pollExport(exportId: string, count: number) {
    if (count >= 60) {
      this.setData({ state: 'failed', error: '导出超时，请稍后重试。' });
      return;
    }
    const timer = setTimeout(async () => {
      try {
        const job = await api.exports.get(exportId);
        const progress = typeof job.progress === 'number' ? job.progress : 0;
        this.setData({ job, progress, pollCount: count + 1 });
        if (job.status === 'ready') {
          this.markReady(job);
          return;
        }
        if (job.status === 'failed' || job.status === 'expired') {
          this.setData({ state: 'failed', error: '导出任务失败或已过期，请重新生成。' });
          return;
        }
        this.pollExport(exportId, count + 1);
      } catch (error) {
        this.setData({ state: 'failed', error: toErrorMessage(error) });
      }
    }, 1000);
    this.setData({ pollTimerId: timer });
  },

  markReady(job: ExportJob) {
    this.setData({
      state: 'ready',
      job,
      progress: 100,
      fileSizeLabel: formatBytes(job.file_size),
      expiresAtLabel: formatDateTime(job.expires_at),
    });
    wx.showToast({ title: '导出完成', icon: 'success' });
  },

  handleDownload() {
    const job = this.data.job;
    if (!job || job.status !== 'ready') {
      wx.showToast({ title: '文件尚未生成', icon: 'none' });
      return;
    }
    const url = this.downloadUrl(job);
    if (!url) {
      wx.showToast({ title: '下载地址不可用', icon: 'none' });
      return;
    }
    const header: Record<string, string> = {};
    const token = getToken();
    if (token) {
      header.Authorization = `Bearer ${token}`;
    }
    wx.showLoading({ title: '下载中', mask: true });
    wx.downloadFile({
      url,
      header,
      success: (res) => {
        if (res.statusCode !== 200) {
          wx.hideLoading();
          wx.showToast({ title: '下载失败，请重新导出', icon: 'none' });
          return;
        }
        this.handleDownloadedFile(res.tempFilePath, job.format, url);
      },
      fail: () => {
        wx.hideLoading();
        wx.showToast({ title: '下载失败，请检查网络', icon: 'none' });
      },
    });
  },

  handleDownloadedFile(filePath: string, format: ExportFormat, url: string) {
    if (format === 'png') {
      wx.saveImageToPhotosAlbum({
        filePath,
        success: () => {
          wx.hideLoading();
          wx.showToast({ title: '已保存到相册', icon: 'success' });
        },
        fail: (error) => {
          wx.hideLoading();
          const message = error.errMsg || '';
          if (message.indexOf('auth') >= 0 || message.indexOf('deny') >= 0) {
            wx.showModal({
              title: '需要相册权限',
              content: '请在设置中允许保存到相册，然后重新下载。',
              confirmText: '去设置',
              success: (result) => {
                if (result.confirm) {
                  wx.openSetting({});
                }
              },
            });
            return;
          }
          wx.showToast({ title: '保存失败，可重试', icon: 'none' });
        },
      });
      return;
    }
    if (format === 'pdf' || format === 'xlsx') {
      wx.openDocument({
        filePath,
        fileType: format,
        showMenu: true,
        success: () => {
          wx.hideLoading();
        },
        fail: () => {
          wx.hideLoading();
          wx.showToast({ title: '打开文件失败，请重试', icon: 'none' });
        },
      });
      return;
    }
    wx.hideLoading();
    wx.showModal({
      title: 'CSV 已下载',
      content: '小程序不支持 CSV 预览，可复制临时下载链接在浏览器中打开。',
      confirmText: '复制链接',
      success: (result) => {
        if (result.confirm) {
          wx.setClipboardData({ data: url });
        }
      },
    });
  },

  downloadUrl(job: ExportJob): string {
    if (job.download_url) {
      if (/^https?:\/\//i.test(job.download_url)) {
        return job.download_url;
      }
      return resolveApiUrl(job.download_url);
    }
    return api.exports.downloadUrl(job.export_id);
  },

  handleRetry() {
    this.handleGenerate();
  },

  goApply() {
    wx.navigateTo({ url: '/pages/apply/apply' });
  },

  goBack() {
    wx.navigateBack({
      fail: () => {
        wx.switchTab({ url: '/pages/home/home' });
      },
    });
  },

  onUnload() {
    if (this.data.pollTimerId) {
      clearTimeout(this.data.pollTimerId);
    }
  },
});

function buildFormats(): FormatOption[] {
  return [
    {
      key: 'png',
      label: 'PNG 图片',
      description: '单页汇报卡，适合微信转发',
      note: '上限 3 MB',
      disabled: false,
      extension: '.png',
    },
    {
      key: 'pdf',
      label: 'PDF 文档',
      description: 'A4 纵向，适合打印与归档',
      note: '上限 10 MB',
      disabled: false,
      extension: '.pdf',
    },
    {
      key: 'xlsx',
      label: 'XLSX 表格',
      description: '摘要、数据、引用三个工作表',
      note: '上限 10 MB',
      disabled: false,
      extension: '.xlsx',
    },
    {
      key: 'csv',
      label: 'CSV 单表',
      description: '仅第一张表；多表请选 XLSX',
      note: '上限 5 MB',
      disabled: false,
      extension: '.csv',
    },
  ];
}

function sanitizeTitle(title: string): string {
  return title.replace(/[\\/:*?"<>|]/g, ' ').replace(/\s+/g, ' ').trim().slice(0, 60);
}

function safeDecode(value: string): string {
  try {
    return decodeURIComponent(value);
  } catch (error) {
    return value;
  }
}
