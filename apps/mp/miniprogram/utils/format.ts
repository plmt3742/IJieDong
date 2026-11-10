/** Number, unit, date and label formatting. Null is never rendered as zero. */

const EMPTY = '暂无数据';

export function toFiniteNumber(value: number | string | null | undefined): number | null {
  if (value === null || value === undefined || value === '') {
    return null;
  }
  const parsed = typeof value === 'number' ? value : Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

export function formatNumber(value: number | null | undefined, precision = 0): string {
  const parsed = toFiniteNumber(value ?? null);
  if (parsed === null) {
    return EMPTY;
  }
  const safePrecision = Math.max(0, Math.min(6, Math.trunc(precision)));
  const fixed = Math.abs(parsed).toFixed(safePrecision);
  const parts = fixed.split('.');
  const integer = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, ',');
  const decimal = parts.length > 1 ? `.${parts[1]}` : '';
  return `${parsed < 0 ? '-' : ''}${integer}${decimal}`;
}

export function formatMetricValue(
  value: number | string | null | undefined,
  precision = 0,
  emptyText = EMPTY
): string {
  if (value === null || value === undefined || value === '') {
    return emptyText;
  }
  if (typeof value === 'string') {
    return value;
  }
  return formatNumber(value, precision);
}

export function formatWithUnit(value: number | null | undefined, unit: string, precision = 0): string {
  const formatted = formatNumber(value, precision);
  if (formatted === EMPTY) {
    return EMPTY;
  }
  return unit ? `${formatted} ${unit}` : formatted;
}

export function formatPercent(value: number | null | undefined, precision = 1): string {
  const parsed = toFiniteNumber(value ?? null);
  if (parsed === null) {
    return EMPTY;
  }
  return `${formatNumber(parsed, precision)}%`;
}

export function formatDate(value: string | null | undefined): string {
  if (!value) {
    return '';
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return `${date.getFullYear()}-${pad2(date.getMonth() + 1)}-${pad2(date.getDate())}`;
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) {
    return '';
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return `${formatDate(value)} ${pad2(date.getHours())}:${pad2(date.getMinutes())}`;
}

export function formatYear(year: number | string | null | undefined): string {
  if (year === null || year === undefined || year === '') {
    return '';
  }
  return `${year} 年`;
}

export function formatBytes(bytes: number | null | undefined): string {
  const parsed = toFiniteNumber(bytes ?? null);
  if (parsed === null || parsed <= 0) {
    return '';
  }
  if (parsed < 1024) {
    return `${parsed} B`;
  }
  if (parsed < 1024 * 1024) {
    return `${(parsed / 1024).toFixed(1)} KB`;
  }
  return `${(parsed / (1024 * 1024)).toFixed(2)} MB`;
}

export function formatStatus(status: string): string {
  const labels: Record<string, string> = {
    none: '未申请',
    pending: '审核中',
    approved: '已批准',
    rejected: '已驳回',
    active: '已启用',
    disabled: '已禁用',
    queued: '排队中',
    running: '生成中',
    ready: '已完成',
    failed: '失败',
    expired: '已过期',
    success: '成功',
    partial: '部分成功',
  };
  return labels[status] || status;
}

export function qualityLabel(status: string): string {
  const labels: Record<string, string> = {
    verified: '已核验',
    estimated: '估算值',
    provisional: '初步值',
    missing: '暂无数据',
    not_applicable: '不适用',
    suppressed: '已抑制',
  };
  return labels[status] || '';
}

export function qualityTone(status: string): string {
  if (status === 'verified') {
    return 'success';
  }
  if (status === 'estimated' || status === 'provisional') {
    return 'warning';
  }
  return 'muted';
}

export function levelLabel(level: string): string {
  const labels: Record<string, string> = {
    district: '区级',
    town: '镇街',
    village: '村居',
  };
  return labels[level] || level;
}

export function levelShortLabel(level: string): string {
  const labels: Record<string, string> = {
    district: '区',
    town: '镇街',
    village: '村居',
  };
  return labels[level] || level;
}

export function categoryLabel(category: string): string {
  return category === 'development_zone' ? '开发区/生态城' : '行政区';
}

export function precisionForCode(code: string): number {
  const decimals: Record<string, number> = {
    area: 2,
    farmland_area: 2,
    forest_area: 2,
    gdp: 2,
    budget_revenue: 2,
    budget_expenditure: 2,
    import_export_total: 2,
    fixed_asset_investment: 2,
    retail_sales: 2,
    population_resident: 0,
    population_household: 0,
    admin_village_count: 0,
  };
  return decimals[code] ?? 0;
}

export function unitForCode(code: string): string {
  const units: Record<string, string> = {
    area: '平方公里',
    farmland_area: '亩',
    forest_area: '亩',
    gdp: '亿元',
    budget_revenue: '亿元',
    budget_expenditure: '亿元',
    import_export_total: '亿元',
    fixed_asset_investment: '亿元',
    retail_sales: '亿元',
    population_resident: '人',
    population_household: '人',
    admin_village_count: '个',
  };
  return units[code] ?? '';
}

export function labelForCode(code: string): string {
  const labels: Record<string, string> = {
    area: '区域面积',
    population_resident: '常住人口',
    population_household: '户籍人口数',
    gdp: '地区生产总值',
    budget_revenue: '地方一般公共预算收入',
    budget_expenditure: '地方一般公共预算支出',
    admin_village_count: '行政村数量',
    farmland_area: '耕地面积',
    forest_area: '林地面积',
    import_export_total: '进出口总额',
    fixed_asset_investment: '固定资产投资',
    retail_sales: '社会消费品零售总额',
  };
  return labels[code] || code;
}

export function maskPhone(phone: string | null | undefined): string {
  if (!phone || phone.length < 7) {
    return phone || '';
  }
  return `${phone.slice(0, 3)}****${phone.slice(-4)}`;
}

export function truncate(text: string, maxLength: number): string {
  if (text.length <= maxLength) {
    return text;
  }
  return `${text.slice(0, maxLength)}…`;
}

export function formatDuration(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds < 0) {
    return '';
  }
  if (seconds < 60) {
    return `${Math.round(seconds)} 秒`;
  }
  const minutes = Math.floor(seconds / 60);
  const rest = Math.round(seconds % 60);
  return `${minutes} 分 ${rest} 秒`;
}

function pad2(value: number): string {
  return value < 10 ? `0${value}` : `${value}`;
}
