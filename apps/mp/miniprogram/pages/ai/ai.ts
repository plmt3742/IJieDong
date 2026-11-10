import {
  canUseGuestAi,
  getIdentity,
  guestQuotaText,
} from '../../utils/auth';
import type { IdentityView } from '../../types/models';
import { setStorage, STORAGE_KEYS } from '../../utils/storage';

interface ExampleQuestion {
  key: string;
  label: string;
  question: string;
}

Page({
  data: {
    identity: null as IdentityView | null,
    locked: false,
    question: '',
    submitting: false,
    error: '',
    quotaText: '',
    examples: [
      {
        key: 'value',
        label: '数值查询',
        question: '2025 年揭东区地区生产总值是多少？',
      },
      {
        key: 'rank',
        label: '排名',
        question: '2025 年各镇街常住人口排名前 5 是哪些？',
      },
      {
        key: 'compare',
        label: '对比',
        question: '2025 年曲溪街道和云路镇常住人口对比如何？',
      },
    ] as ExampleQuestion[],
  },

  onLoad() {
    this.refreshIdentity();
  },

  onShow() {
    this.refreshIdentity();
    if (this.data.submitting) {
      this.setData({ submitting: false });
    }
  },

  refreshIdentity() {
    const identity = getIdentity();
    this.setData({
      identity,
      locked: !identity.canUseAi,
      quotaText: guestQuotaText(),
    });
  },

  handleInput(event: WechatMiniprogram.Input) {
    this.setData({ question: event.detail.value });
  },

  handleExample(event: WechatMiniprogram.TouchEvent) {
    const index = Number(event.currentTarget.dataset.index);
    const example = this.data.examples[index];
    if (example) {
      this.setData({ question: example.question });
    }
  },

  handleSend() {
    if (this.data.locked) {
      wx.showToast({ title: '申请审核中，暂不能使用 AI', icon: 'none' });
      return;
    }
    const question = this.data.question.trim();
    if (!question) {
      wx.showToast({ title: '请输入问题', icon: 'none' });
      return;
    }
    const identity = getIdentity();
    if (identity.isGuest && !canUseGuestAi()) {
      wx.showModal({
        title: '今日 AI 次数已用完',
        content: '游客每日可使用 5 次 AI。申请账号并通过后可继续使用。',
        confirmText: '去申请',
        success: (result) => {
          if (result.confirm) {
            this.goApply();
          }
        },
      });
      return;
    }
    this.setData({ submitting: true, error: '' });
    setStorage(STORAGE_KEYS.pendingQuestion, question);
    wx.navigateTo({
      url: `/pages/chat/chat?question=${encodeURIComponent(question)}`,
      fail: () => {
        this.setData({ error: '无法打开会话，请重试。' });
      },
      complete: () => {
        this.setData({ submitting: false });
      },
    });
  },

  goApply() {
    wx.navigateTo({ url: '/pages/apply/apply' });
  },
});
