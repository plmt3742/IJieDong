import {
  formatNumber,
  qualityLabel,
  qualityTone,
  toFiniteNumber,
} from '../../utils/format';

Component({
  properties: {
    code: {
      type: String,
      value: '',
    },
    label: {
      type: String,
      value: '',
    },
    value: {
      type: null,
      value: null,
    },
    unit: {
      type: String,
      value: '',
    },
    year: {
      type: Number,
      value: 0,
    },
    status: {
      type: String,
      value: '',
    },
    precision: {
      type: Number,
      value: 0,
    },
    emptyText: {
      type: String,
      value: '暂无数据',
    },
    hint: {
      type: String,
      value: '',
    },
    disabled: {
      type: Boolean,
      value: false,
    },
  },

  data: {
    display: '暂无数据',
    showUnit: false,
    note: '',
    tone: 'muted',
    isEmpty: true,
  },

  observers: {
    'value, unit, precision, status, emptyText': function (
      value: number | string | null,
      unit: string,
      precision: number,
      status: string,
      emptyText: string
    ) {
      const parsed = toFiniteNumber(value);
      const isNotApplicable = status === 'not_applicable';
      const isEmpty = parsed === null;
      const display = isNotApplicable
        ? '不适用'
        : isEmpty
          ? emptyText || '暂无数据'
          : formatNumber(parsed, precision);
      this.setData({
        display,
        showUnit: !isNotApplicable && !isEmpty && !!unit,
        note: qualityLabel(status),
        tone: qualityTone(status),
        isEmpty: isEmpty && !isNotApplicable,
      });
    },
  },

  methods: {
    handleTap() {
      if (this.data.disabled) {
        return;
      }
      this.triggerEvent('cardtap', { code: this.data.code, label: this.data.label });
    },
  },
});
