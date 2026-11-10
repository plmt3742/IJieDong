import { api, buildDemoAnswer, normalizeAnswerBlocks } from '../../services/api';
import { DEFAULT_PERIOD_YEAR } from '../../services/config';
import {
  ApiError,
  isFeatureUnavailable,
  toErrorMessage,
} from '../../services/request';
import type {
  AIChatResponse,
  AnswerAction,
  AnswerBlock,
  Citation,
} from '../../types/api';
import type { ChatMessageModel, IdentityView } from '../../types/models';
import {
  canUseGuestAi,
  getGuestAiRemaining,
  getIdentity,
  guestAiLimit,
  guestQuotaText,
  recordGuestAiUse,
} from '../../utils/auth';
import { formatNumber } from '../../utils/format';
import { getStorage, removeStorage, STORAGE_KEYS } from '../../utils/storage';

let seed = 0;

Page({
  data: {
    identity: null as IdentityView | null,
    locked: false,
    messages: [] as ChatMessageModel[],
    input: '',
    sending: false,
    state: 'idle' as string,
    scrollIntoView: '',
    quotaText: '',
    sessionId: null as number | null,
    guestRemaining: 0,
    guestLimit: 5,
  },

  onLoad(query: Record<string, string | undefined>) {
    const identity = getIdentity();
    const locked = !identity.canUseAi;
    this.setData({
      identity,
      locked,
      quotaText: guestQuotaText(),
      guestRemaining: getGuestAiRemaining(),
      guestLimit: guestAiLimit(),
    });
    if (locked) {
      return;
    }
    const queryQuestion = query.question ? safeDecode(query.question) : '';
    const pending = getStorage<string>(STORAGE_KEYS.pendingQuestion, '');
    removeStorage(STORAGE_KEYS.pendingQuestion);
    const question = queryQuestion || pending;
    if (question) {
      this.setData({ input: question });
      this.ask(question, true);
    }
  },

  onShow() {
    const identity = getIdentity();
    this.setData({
      identity,
      locked: !identity.canUseAi,
      quotaText: guestQuotaText(),
      guestRemaining: getGuestAiRemaining(),
    });
  },

  handleInput(event: WechatMiniprogram.Input) {
    this.setData({ input: event.detail.value });
  },

  handleSend() {
    const question = this.data.input.trim();
    if (!question) {
      wx.showToast({ title: '请输入问题', icon: 'none' });
      return;
    }
    this.ask(question, true);
  },

  handleFollowUp(event: WechatMiniprogram.TouchEvent) {
    const question = String(event.currentTarget.dataset.question || '');
    if (question) {
      this.ask(question, true);
    }
  },

  handleRetry(event: WechatMiniprogram.TouchEvent) {
    const question = String(event.currentTarget.dataset.question || '');
    if (question) {
      this.ask(question, false);
    }
  },

  async ask(question: string, appendUser: boolean) {
    if (this.data.locked || this.data.sending) {
      return;
    }
    const identity = getIdentity();
    if (identity.isGuest && !canUseGuestAi()) {
      wx.showModal({
        title: '今日 AI 次数已用完',
        content: `游客每日可使用 ${guestAiLimit()} 次 AI，申请账号通过后可继续使用。`,
        confirmText: '去申请',
        success: (result) => {
          if (result.confirm) {
            this.goApply();
          }
        },
      });
      return;
    }

    if (identity.isGuest) {
      recordGuestAiUse();
    }

    const assistantId = nextId('a');
    const assistant: ChatMessageModel = {
      id: assistantId,
      role: 'assistant',
      text: '',
      question,
      blocks: [],
      citations: [],
      followUps: [],
      state: 'thinking',
      errorText: '',
      demo: false,
      hasSourceBlock: false,
      time: clock(),
    };
    const messages = this.data.messages.slice();
    if (appendUser) {
      messages.push({
        id: nextId('u'),
        role: 'user',
        text: question,
        question,
        blocks: [],
        citations: [],
        followUps: [],
        state: 'done',
        errorText: '',
        demo: false,
        hasSourceBlock: false,
        time: clock(),
      });
    }
    messages.push(assistant);

    this.setData(
      {
        messages,
        input: '',
        sending: true,
        state: 'thinking',
        quotaText: guestQuotaText(),
        guestRemaining: getGuestAiRemaining(),
      },
      () => {
        this.scrollTo(assistantId);
      }
    );

    try {
      const response = await api.ai.chat({
        session_id: this.data.sessionId,
        question,
        context: { period: String(DEFAULT_PERIOD_YEAR) },
      });
      this.applyAnswer(assistantId, response);
    } catch (error) {
      if (isFeatureUnavailable(error)) {
        this.applyAnswer(assistantId, buildDemoAnswer(question));
        return;
      }
      const message = toErrorMessage(error);
      this.updateMessage(assistantId, {
        state: 'error',
        errorText:
          error instanceof ApiError && error.code === 'RATE_LIMITED'
            ? '提问过于频繁，请稍后再试。'
            : message,
      });
      this.setData({ sending: false, state: 'error', quotaText: guestQuotaText() });
      this.scrollTo(assistantId);
    }
  },

  applyAnswer(messageId: string, response: AIChatResponse) {
    const blocks = decorateBlocks(normalizeAnswerBlocks(response));
    const citations = (response.citations || []).map((citation, index) => ({
      ...citation,
      citation_id: citation.citation_id || `cit-${index}`,
    }));
    const state = response.status === 'refused' ? 'refused' : 'done';
    this.updateMessage(messageId, {
      state,
      blocks,
      citations,
      followUps: response.follow_up_questions || [],
      demo: !!response.demo,
      hasSourceBlock: blocks.some((block) => block.type === 'source'),
      errorText: '',
    });
    this.setData({
      sending: false,
      state,
      sessionId: response.session_id === undefined ? this.data.sessionId : response.session_id,
      quotaText: guestQuotaText(),
      guestRemaining: getGuestAiRemaining(),
    });
    this.scrollTo(messageId);
  },

  updateMessage(messageId: string, patch: Partial<ChatMessageModel>) {
    const messages = this.data.messages.map((message) =>
      message.id === messageId ? { ...message, ...patch } : message
    );
    this.setData({ messages });
  },

  scrollTo(messageId: string) {
    this.setData({ scrollIntoView: `msg-${messageId}` });
  },

  handleAction(event: WechatMiniprogram.TouchEvent) {
    const action = event.currentTarget.dataset.action as AnswerAction | undefined;
    if (!action) {
      return;
    }
    if (action.type === 'navigate' && action.url) {
      if (
        action.url.indexOf('/pages/regions/') === 0 ||
        action.url.indexOf('/pages/ai/') === 0 ||
        action.url.indexOf('/pages/home/') === 0
      ) {
        wx.switchTab({ url: action.url });
      } else {
        wx.navigateTo({ url: action.url });
      }
      return;
    }
    if (action.type === 'export') {
      wx.navigateTo({
        url:
          `/pages/export/export?region_id=${action.region_id || 0}` +
          `&indicator_id=${action.indicator_id || 0}` +
          `&indicator_code=${encodeURIComponent(action.indicator_code || '')}` +
          `&period_year=${action.period || DEFAULT_PERIOD_YEAR}`,
      });
      return;
    }
    if (action.type === 'apply') {
      this.goApply();
      return;
    }
    if (action.type === 'retry') {
      const lastQuestion = this.lastUserQuestion();
      if (lastQuestion) {
        this.ask(lastQuestion, false);
      }
    }
  },

  handleCitation(event: WechatMiniprogram.TouchEvent) {
    const citation = event.currentTarget.dataset.citation as Citation | undefined;
    if (!citation) {
      return;
    }
    if (!citation.region_id || (!citation.indicator_id && !citation.indicator_code)) {
      wx.showToast({ title: '引用缺少跳转参数', icon: 'none' });
      return;
    }
    wx.navigateTo({
      url:
        `/pages/indicator-detail/indicator-detail?region_id=${citation.region_id}` +
        `&indicator_id=${citation.indicator_id || 0}` +
        `&indicator_code=${encodeURIComponent(citation.indicator_code || '')}` +
        `&period_year=${citation.period || DEFAULT_PERIOD_YEAR}`,
    });
  },

  lastUserQuestion(): string {
    const messages = this.data.messages.filter((message) => message.role === 'user');
    if (!messages.length) {
      return '';
    }
    return messages[messages.length - 1].question;
  },

  goApply() {
    wx.navigateTo({ url: '/pages/apply/apply' });
  },

  onUnload() {
    removeStorage(STORAGE_KEYS.pendingQuestion);
  },
});

function decorateBlocks(blocks: AnswerBlock[]): AnswerBlock[] {
  return blocks.map((block, index) => {
    const next: AnswerBlock = { ...block, key: `${index}-${block.type}` };
    if (block.type === 'metric_grid' && block.metrics) {
      next.metrics = block.metrics.map((metric) => ({
        ...metric,
        display: formatMetric(metric.value),
      }));
    }
    if (block.type === 'table') {
      const rows = block.rows || [];
      const precision = detectPrecision(rows);
      next.tableColumns = block.columns || [];
      next.tableRows = rows.map((row, rowIndex) => ({
        id: rowIndex,
        cells: row.map((cell) => formatCell(cell, precision)),
      }));
    }
    if (block.type === 'ranking') {
      const precision = (block.ranking || []).some(
        (item) => item.value !== null && !Number.isInteger(item.value)
      )
        ? 2
        : 0;
      next.rankingView = (block.ranking || []).map((item) => ({
        rank: item.rank,
        name: item.name,
        value:
          item.value === null
            ? '暂无数据'
            : `${formatNumber(item.value, precision)}${item.unit ? ` ${item.unit}` : ''}`,
      }));
    }
    return next;
  });
}

function formatMetric(value: number | string | null): string {
  if (value === null || value === undefined || value === '') {
    return '暂无数据';
  }
  if (typeof value === 'string') {
    return value;
  }
  return formatNumber(value, Number.isInteger(value) ? 0 : 2);
}

function detectPrecision(rows: Array<Array<string | number | null>>): number {
  const values: number[] = [];
  rows.forEach((row) => {
    row.forEach((cell) => {
      if (typeof cell === 'number' && Number.isFinite(cell)) {
        values.push(cell);
      }
    });
  });
  if (!values.length) {
    return 0;
  }
  return values.every((value) => Number.isInteger(value)) ? 0 : 2;
}

function formatCell(cell: string | number | null, precision: number): string {
  if (cell === null || cell === undefined || cell === '') {
    return '暂无数据';
  }
  if (typeof cell === 'number') {
    return formatNumber(cell, precision);
  }
  return cell;
}

function nextId(prefix: string): string {
  seed += 1;
  return `${prefix}-${Date.now()}-${seed}`;
}

function clock(): string {
  const date = new Date();
  const hour = date.getHours();
  const minute = date.getMinutes();
  return `${hour < 10 ? `0${hour}` : hour}:${minute < 10 ? `0${minute}` : minute}`;
}

function safeDecode(value: string): string {
  try {
    return decodeURIComponent(value);
  } catch (error) {
    return value;
  }
}
