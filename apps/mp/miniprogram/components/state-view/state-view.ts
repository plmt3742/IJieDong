Component({
  properties: {
    state: {
      type: String,
      value: 'empty',
    },
    title: {
      type: String,
      value: '',
    },
    description: {
      type: String,
      value: '',
    },
    actionText: {
      type: String,
      value: '',
    },
    secondaryText: {
      type: String,
      value: '',
    },
    requestId: {
      type: String,
      value: '',
    },
    compact: {
      type: Boolean,
      value: false,
    },
  },

  data: {
    heading: '',
    detail: '',
  },

  observers: {
    'state, title, description': function (state: string, title: string, description: string) {
      const defaults: Record<string, { heading: string; detail: string }> = {
        loading: { heading: '正在加载', detail: '请稍候，数据正在准备中。' },
        empty: { heading: '暂无数据', detail: '当前条件下没有可展示的数据。' },
        error: { heading: '加载失败', detail: '请检查网络后重试。' },
        locked: { heading: '需要账号权限', detail: '申请通过前只能查看申请状态。' },
        'no-permission': { heading: '暂无访问权限', detail: '当前身份不能访问该功能。' },
        'not-applicable': { heading: '不适用', detail: '该指标不适用于当前区域层级或类型。' },
      };
      const fallback = defaults[state] || defaults.empty;
      this.setData({
        heading: title || fallback.heading,
        detail: description || fallback.detail,
      });
    },
  },

  methods: {
    handleAction() {
      this.triggerEvent('action');
    },
    handleSecondary() {
      this.triggerEvent('secondary');
    },
  },
});
