import { api } from '../../services/api';
import {
  APP_VERSION,
  DEMO_MODE,
  MAINTAINER_PHONE,
  MAINTAINER_PHONE_DISPLAY,
  getApiBaseUrl,
} from '../../services/config';
import { isAuthError, isFeatureUnavailable } from '../../services/request';
import type { ApplicationTimelineItem, AuthUser } from '../../types/api';
import type { IdentityView } from '../../types/models';
import {
  buildApplicationTimeline,
  canResubmit,
  resubmitHint,
} from '../../utils/application';
import {
  clearSession,
  getApplication,
  getIdentity,
  getUser,
  saveApplication,
  setUser,
  type StoredApplication,
} from '../../utils/auth';
import { formatDateTime, formatStatus } from '../../utils/format';

interface HelpItem {
  key: string;
  title: string;
  hint: string;
}

Page({
  data: {
    identity: null as IdentityView | null,
    user: null as AuthUser | null,
    application: null as StoredApplication | null,
    timeline: [] as ApplicationTimelineItem[],
    statusLabel: '',
    statusTone: 'muted',
    resubmitHint: '',
    canResubmitNow: false,
    avatarText: '游',
    submittedAtLabel: '',
    reviewedAtLabel: '',
    helpItems: [
      { key: 'guide', title: '使用指南', hint: '浏览、问答与导出' },
      { key: 'caliber', title: '数据口径', hint: '单位、年份与空值规则' },
      { key: 'privacy', title: '隐私说明', hint: '收集字段与使用范围' },
      { key: 'phone', title: '维护电话', hint: MAINTAINER_PHONE_DISPLAY },
      { key: 'about', title: '关于应用', hint: 'Demo v0' },
      { key: 'version', title: '版本号', hint: APP_VERSION },
    ] as HelpItem[],
    version: APP_VERSION,
    apiBase: '',
    phoneDisplay: MAINTAINER_PHONE_DISPLAY,
    demoMode: DEMO_MODE,
    year: 2025,
  },

  onLoad() {
    this.refresh();
  },

  onShow() {
    this.refresh();
    this.syncMe();
    this.syncStatus();
  },

  refresh() {
    const identity = getIdentity();
    const user = getUser();
    const application = getApplication();
    const status = application ? application.status : 'none';
    this.setData({
      identity,
      user,
      application,
      statusLabel: formatStatus(status),
      statusTone: statusTone(status),
      timeline: application ? buildApplicationTimeline(application) : [],
      canResubmitNow: canResubmit(application),
      resubmitHint: resubmitHint(application),
      avatarText: identity.name ? identity.name.slice(0, 1) : '游',
      submittedAtLabel: application ? formatDateTime(application.submitted_at) : '',
      reviewedAtLabel: application ? formatDateTime(application.reviewed_at) : '',
      apiBase: getApiBaseUrl() || '未配置',
    });
  },

  async syncMe() {
    if (!getUser()) {
      return;
    }
    try {
      const user = await api.auth.me();
      setUser(user);
      this.refresh();
    } catch (error) {
      if (isAuthError(error)) {
        clearSession();
        this.refresh();
      }
    }
  },

  async syncStatus() {
    const application = getApplication();
    if (!application || !application.status_token) {
      return;
    }
    try {
      const status = await api.auth.applicationStatus(
        application.application_no,
        application.status_token
      );
      saveApplication({
        ...application,
        ...status,
        phone: application.phone,
        reason: application.reason,
        demo: application.demo,
      });
      this.refresh();
    } catch (error) {
      if (isAuthError(error)) {
        clearSession();
        this.refresh();
      }
    }
  },

  handleHelp(event: WechatMiniprogram.TouchEvent) {
    const key = String(event.currentTarget.dataset.key || '');
    const contents: Record<string, string> = {
      guide:
        '首页查看区级核心指标；区域页按区、镇街、村居浏览；点击指标卡进入详情；问答页可用自然语言查询。导出需已批准账号。',
      caliber:
        '单位以指标元数据为准，不在前端换算。空值显示“暂无数据”，不适用的指标显示“不适用”，均不以 0 代替。演示数据来自确定性合成种子。',
      privacy:
        '账号申请仅收集姓名、单位、手机号和申请说明，用于身份核对与审批联系；不收集身份证号、住址、人脸等敏感信息。状态令牌只保存在本机。',
      about:
        'i揭东是面向揭东区公职人员的政府数据门户 Demo v0，包含区、镇街、村居三级数据浏览、数据问答与汇报导出。当前为演示环境，数据均为合成数据。',
      version: `当前版本：${APP_VERSION}\nAPI 地址：${getApiBaseUrl() || '未配置'}\n数据环境：演示数据（合成）`,
    };
    if (key === 'phone') {
      this.callMaintainer();
      return;
    }
    wx.showModal({
      title: contents[key] ? this.helpTitle(key) : '说明',
      content: contents[key] || '暂无说明。',
      showCancel: false,
      confirmText: '知道了',
    });
  },

  helpTitle(key: string): string {
    const item = this.data.helpItems.find((entry) => entry.key === key);
    return item ? item.title : '说明';
  },

  callMaintainer() {
    if (MAINTAINER_PHONE) {
      wx.makePhoneCall({ phoneNumber: MAINTAINER_PHONE });
      return;
    }
    wx.showModal({
      title: '维护电话',
      content: '演示环境未配置维护电话。正式部署前请在本地配置 MAINTAINER_PHONE。',
      showCancel: false,
      confirmText: '知道了',
    });
  },

  goApply() {
    wx.navigateTo({ url: '/pages/apply/apply' });
  },

  goAdmin() {
    if (!this.data.identity || !this.data.identity.canManage) {
      wx.showToast({ title: '当前角色无管理权限', icon: 'none' });
      return;
    }
    wx.navigateTo({ url: '/pages/admin-approval/admin-approval' });
  },

  handleLogout() {
    wx.showModal({
      title: '退出登录',
      content: '退出后将清除本机令牌并回到游客模式。',
      confirmText: '退出',
      success: (result) => {
        if (!result.confirm) {
          return;
        }
        api.auth
          .logout()
          .catch(() => undefined)
          .then(() => {
            clearSession();
            this.refresh();
            wx.showToast({ title: '已退出登录', icon: 'none' });
            wx.switchTab({ url: '/pages/home/home' });
          });
      },
    });
  },

  copyApplicationNo() {
    const application = this.data.application;
    if (!application) {
      return;
    }
    wx.setClipboardData({
      data: application.application_no,
      success: () => {
        wx.showToast({ title: '申请编号已复制', icon: 'none' });
      },
    });
  },

  handleApplicationAction() {
    this.goApply();
  },

  handleResubmit() {
    if (!this.data.canResubmitNow) {
      wx.showToast({ title: this.data.resubmitHint || '暂不可重提', icon: 'none' });
      return;
    }
    wx.navigateTo({ url: '/pages/apply/apply?resubmit=1' });
  },
});

function statusTone(status: string): string {
  if (status === 'pending') {
    return 'warning';
  }
  if (status === 'approved' || status === 'active') {
    return 'success';
  }
  if (status === 'rejected' || status === 'disabled') {
    return 'danger';
  }
  return 'muted';
}
