import { api } from '../../services/api';
import {
  MAINTAINER_PHONE,
  MAINTAINER_PHONE_DISPLAY,
} from '../../services/config';
import {
  isFeatureUnavailable,
  toErrorMessage,
} from '../../services/request';
import type { ApplicationTimelineItem } from '../../types/api';
import {
  buildApplicationTimeline,
  canResubmit,
  resubmitHint,
} from '../../utils/application';
import {
  getApplication,
  saveApplication,
  type StoredApplication,
} from '../../utils/auth';
import { formatDateTime, formatStatus } from '../../utils/format';

interface ApplicationForm {
  display_name: string;
  unit: string;
  phone: string;
  reason: string;
}

Page({
  data: {
    mode: 'form' as 'form' | 'status',
    form: {
      display_name: '',
      unit: '',
      phone: '',
      reason: '',
    } as ApplicationForm,
    privacyConsent: false,
    errors: {} as Record<string, string>,
    submitting: false,
    application: null as StoredApplication | null,
    timeline: [] as ApplicationTimelineItem[],
    statusLabel: '',
    statusTone: 'muted',
    submittedAtLabel: '',
    reviewedAtLabel: '',
    canResubmitNow: false,
    resubmitHint: '',
    statusNo: '',
    statusToken: '',
    statusLoading: false,
    statusError: '',
    phoneDisplay: MAINTAINER_PHONE_DISPLAY,
  },

  onLoad(query: Record<string, string | undefined>) {
    const application = getApplication();
    const wantResubmit = query.resubmit === '1';
    if (application && wantResubmit && canResubmit(application)) {
      this.setData({
        mode: 'form',
        form: {
          display_name: application.display_name || '',
          unit: application.unit || '',
          phone: application.phone || '',
          reason: application.reason || '',
        },
      });
      return;
    }
    if (application) {
      this.showStatus(application);
      return;
    }
    this.setData({ mode: 'form' });
  },

  handleField(event: WechatMiniprogram.Input) {
    const field = String(event.currentTarget.dataset.field || '');
    if (!field) {
      return;
    }
    const value = event.detail.value;
    this.setData({
      [`form.${field}`]: value,
      [`errors.${field}`]: '',
    });
  },

  togglePrivacy() {
    this.setData({
      privacyConsent: !this.data.privacyConsent,
      'errors.privacy_consent': '',
    });
  },

  showPrivacy() {
    wx.showModal({
      title: '隐私告知',
      content:
        '收集字段：姓名、单位、手机号、申请说明。用途：账号审批与联系。保存期限：按演示环境保留策略执行。访问范围：仅审批管理员可见，列表默认掩码手机号。联系维护：' +
        MAINTAINER_PHONE_DISPLAY +
        '。不收集身份证号、住址、人脸等敏感信息；状态令牌只保存在本机。',
      showCancel: false,
      confirmText: '知道了',
    });
  },

  validate(): Record<string, string> {
    const form = this.data.form;
    const errors: Record<string, string> = {};
    if (form.display_name.trim().length < 2 || form.display_name.trim().length > 20) {
      errors.display_name = '请输入 2 至 20 字的姓名。';
    }
    if (form.unit.trim().length < 2 || form.unit.trim().length > 50) {
      errors.unit = '请输入 2 至 50 字的单位或科室。';
    }
    if (!/^1[3-9]\d{9}$/.test(form.phone.trim())) {
      errors.phone = '请输入有效的中国大陆手机号。';
    }
    if (form.reason.trim().length < 10 || form.reason.trim().length > 200) {
      errors.reason = '申请说明需 10 至 200 字。';
    }
    if (!this.data.privacyConsent) {
      errors.privacy_consent = '请先阅读并同意隐私告知。';
    }
    return errors;
  },

  async submit() {
    if (this.data.submitting) {
      return;
    }
    const errors = this.validate();
    if (Object.keys(errors).length) {
      this.setData({ errors });
      wx.showToast({ title: '请检查表单填写', icon: 'none' });
      return;
    }
    const payload = {
      display_name: this.data.form.display_name.trim(),
      unit: this.data.form.unit.trim(),
      phone: this.data.form.phone.trim(),
      reason: this.data.form.reason.trim(),
      privacy_consent: true,
    };
    this.setData({ submitting: true, statusError: '' });
    try {
      const result = await api.auth.apply(payload);
      const record: StoredApplication = {
        application_no: result.application_no,
        status: result.status,
        status_token: result.status_token,
        submitted_at: result.submitted_at,
        display_name: payload.display_name,
        unit: payload.unit,
        phone: payload.phone,
        reason: payload.reason,
        demo: false,
      };
      this.setData({ submitting: false });
      saveApplication(record);
      this.showStatus(record);
      wx.showToast({ title: '申请已提交', icon: 'success' });
    } catch (error) {
      if (isFeatureUnavailable(error)) {
        const record = this.createDemoApplication(payload);
        this.setData({ submitting: false });
        saveApplication(record);
        this.showStatus(record);
        wx.showToast({ title: '演示模式：仅保存在本机', icon: 'none' });
        return;
      }
      this.setData({
        submitting: false,
        statusError: toErrorMessage(error),
      });
      wx.showModal({
        title: '提交失败',
        content: toErrorMessage(error),
        showCancel: false,
        confirmText: '知道了',
      });
    }
  },

  createDemoApplication(payload: {
    display_name: string;
    unit: string;
    phone: string;
    reason: string;
  }): StoredApplication {
    const now = new Date();
    const stamp = `${now.getFullYear()}${pad2(now.getMonth() + 1)}${pad2(now.getDate())}`;
    const suffix = `${Date.now()}`.slice(-4);
    return {
      application_no: `DEMO-${stamp}-${suffix}`,
      status: 'pending',
      status_token: `demo-${Date.now()}`,
      submitted_at: now.toISOString(),
      display_name: payload.display_name,
      unit: payload.unit,
      phone: payload.phone,
      reason: payload.reason,
      demo: true,
    };
  },

  showStatus(application: StoredApplication) {
    this.setData({
      mode: 'status',
      application,
      timeline: buildApplicationTimeline(application),
      statusLabel: formatStatus(application.status),
      statusTone: tone(application.status),
      submittedAtLabel: formatDateTime(application.submitted_at),
      reviewedAtLabel: formatDateTime(application.reviewed_at),
      canResubmitNow: canResubmit(application),
      resubmitHint: resubmitHint(application),
      statusNo: application.application_no,
      statusToken: application.status_token || '',
      statusError: '',
    });
  },

  handleQueryInput(event: WechatMiniprogram.Input) {
    const field = String(event.currentTarget.dataset.field || '');
    if (field === 'no') {
      this.setData({ statusNo: event.detail.value });
    } else if (field === 'token') {
      this.setData({ statusToken: event.detail.value });
    }
  },

  async queryStatus() {
    const applicationNo = this.data.statusNo.trim();
    const statusToken = this.data.statusToken.trim();
    if (!applicationNo || !statusToken) {
      wx.showToast({ title: '请输入申请编号和状态令牌', icon: 'none' });
      return;
    }
    this.setData({ statusLoading: true, statusError: '' });
    try {
      const result = await api.auth.applicationStatus(applicationNo, statusToken);
      const local = getApplication();
      const record: StoredApplication = {
        ...result,
        status_token: result.status_token || statusToken,
        phone: local ? local.phone : undefined,
        reason: local ? local.reason : undefined,
        demo: false,
      };
      saveApplication(record);
      this.setData({ statusLoading: false });
      this.showStatus(record);
      wx.showToast({ title: '状态已更新', icon: 'none' });
    } catch (error) {
      if (isFeatureUnavailable(error)) {
        const local = getApplication();
        if (
          local &&
          local.application_no === applicationNo &&
          local.status_token === statusToken
        ) {
          this.setData({ statusLoading: false });
          this.showStatus(local);
          wx.showToast({ title: '接口未就绪，展示本机记录', icon: 'none' });
          return;
        }
      }
      this.setData({
        statusLoading: false,
        statusError: toErrorMessage(error),
      });
    }
  },

  switchToForm() {
    const application = this.data.application;
    if (application && application.status !== 'rejected') {
      wx.showToast({ title: '当前申请仍在流程中', icon: 'none' });
      return;
    }
    if (application && !canResubmit(application)) {
      wx.showToast({ title: this.data.resubmitHint || '暂不可重提', icon: 'none' });
      return;
    }
    const form: ApplicationForm = application
      ? {
          display_name: application.display_name || '',
          unit: application.unit || '',
          phone: application.phone || '',
          reason: application.reason || '',
        }
      : { display_name: '', unit: '', phone: '', reason: '' };
    this.setData({ mode: 'form', form, errors: {}, privacyConsent: false });
  },

  copyApplicationNo() {
    if (!this.data.application) {
      return;
    }
    wx.setClipboardData({
      data: this.data.application.application_no,
      success: () => {
        wx.showToast({ title: '申请编号已复制', icon: 'none' });
      },
    });
  },

  contactAdmin() {
    if (MAINTAINER_PHONE) {
      wx.makePhoneCall({ phoneNumber: MAINTAINER_PHONE });
      return;
    }
    wx.showModal({
      title: '联系管理员',
      content: '演示环境未配置维护电话，请联系项目部署人员。',
      showCancel: false,
      confirmText: '知道了',
    });
  },

  goProfile() {
    wx.switchTab({ url: '/pages/profile/profile' });
  },
});

function pad2(value: number): string {
  return value < 10 ? `0${value}` : `${value}`;
}

function tone(status: string): string {
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
