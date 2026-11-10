import type { ChartSeries, ChartSpec } from '../../types/chart';
import { formatNumber, truncate } from '../../utils/format';

interface ChartRow {
  id: number;
  cells: string[];
}

interface ChartData {
  mode: 'chart' | 'table';
  manualTable: boolean;
  isTableOnly: boolean;
  tableColumns: string[];
  tableRows: ChartRow[];
  fallbackNote: string;
  canvasHeight: number;
}

interface ChartDataset {
  categories: string[];
  series: ChartSeries[];
}

const COLORS = ['#1f4e79', '#2f6f9f', '#5c8fb5', '#8fb3ca', '#c2d6e3', '#6b7f8f'];
const AXIS_COLOR = '#5b6573';
const GRID_COLOR = '#e3e8ee';
const EMPTY_CELL = '暂无数据';

Component({
  properties: {
    spec: {
      type: null,
      value: null,
    },
    height: {
      type: Number,
      value: 220,
    },
    showToggle: {
      type: Boolean,
      value: true,
    },
  },

  data: {
    mode: 'chart',
    manualTable: false,
    isTableOnly: false,
    tableColumns: [] as string[],
    tableRows: [] as ChartRow[],
    fallbackNote: '',
    canvasHeight: 220,
  } as ChartData,

  observers: {
    'spec, height': function (spec: ChartSpec | null, height: number) {
      this.prepareChart(spec, height);
    },
  },

  lifetimes: {
    ready() {
      const spec = this.data.spec as ChartSpec | null;
      this.prepareChart(spec, this.data.height);
    },
  },

  methods: {
    prepareChart(spec: ChartSpec | null, height: number) {
      const canvasHeight = height > 0 ? height : 220;
      const table = this.buildTable(spec);
      const canRender = this.canRenderChart(spec);
      const manualTable = this.data.manualTable;
      const mode: 'chart' | 'table' = canRender && !manualTable ? 'chart' : 'table';
      const fallbackNote = canRender
        ? ''
        : spec && spec.type === 'table'
          ? ''
          : '当前数据不足或图表不可用，已使用表格展示。';

      this.setData(
        {
          canvasHeight,
          tableColumns: table.columns,
          tableRows: table.rows,
          isTableOnly: !canRender,
          mode,
          fallbackNote,
        },
        () => {
          if (mode === 'chart') {
            this.drawChart();
          }
        }
      );
    },

    switchMode(event: WechatMiniprogram.TouchEvent) {
      const mode = event.currentTarget.dataset.mode as 'chart' | 'table';
      if (mode === 'table') {
        this.setData({ mode: 'table', manualTable: true });
        return;
      }
      this.setData({ mode: 'chart', manualTable: false }, () => {
        this.drawChart();
      });
    },

    canRenderChart(spec: ChartSpec | null): boolean {
      if (!spec || spec.type === 'table') {
        return false;
      }
      if (!spec.categories || !spec.categories.length || !spec.series || !spec.series.length) {
        return false;
      }
      const values = collectValues(spec);
      if (!values.length) {
        return false;
      }
      if (spec.type === 'pie') {
        return values.some((value) => value > 0);
      }
      return true;
    },

    buildTable(spec: ChartSpec | null): { columns: string[]; rows: ChartRow[] } {
      if (!spec) {
        return { columns: ['项目', '数值'], rows: [] };
      }
      let columns: string[] = [];
      let rawRows: Array<Array<string | number | null>> = [];
      if (spec.type === 'table' || (spec.columns && spec.columns.length)) {
        columns = spec.columns && spec.columns.length ? spec.columns.slice() : ['项目', '数值'];
        rawRows = spec.rows ? spec.rows.slice() : [];
      } else {
        const maxItems = this.maxItems(spec);
        const categories = (spec.categories || []).slice(0, maxItems);
        const series = (spec.series || []).map((item) => ({
          name: item.name,
          values: item.values.slice(0, maxItems),
        }));
        columns = ['项目'].concat(series.map((item) => item.name));
        rawRows = categories.map((category, index) => {
          const row: Array<string | number | null> = [category];
          series.forEach((item) => {
            const value = item.values[index];
            row.push(value === undefined ? null : value);
          });
          return row;
        });
      }
      const precision = detectPrecision(rawRows);
      const rows = rawRows.map((row, rowIndex) => ({
        id: rowIndex,
        cells: row.map((cell) => formatCell(cell, precision)),
      }));
      return { columns, rows };
    },

    maxItems(spec: ChartSpec): number {
      const configured = spec.options && spec.options.max_items ? spec.options.max_items : 15;
      return Math.max(1, Math.min(30, Math.trunc(configured)));
    },

    prepareDataset(spec: ChartSpec): ChartDataset {
      const maxItems = this.maxItems(spec);
      let categories = (spec.categories || []).slice(0, maxItems);
      let series = (spec.series || []).map((item) => ({
        name: item.name,
        values: item.values.slice(0, maxItems),
      }));
      const sort = spec.options ? spec.options.sort : 'none';
      if ((spec.type === 'bar' || spec.type === 'hbar') && sort && sort !== 'none' && series.length) {
        const order = categories.map((_, index) => index);
        order.sort((left, right) => {
          const leftValue = series[0].values[left];
          const rightValue = series[0].values[right];
          if (leftValue === null && rightValue === null) {
            return 0;
          }
          if (leftValue === null) {
            return 1;
          }
          if (rightValue === null) {
            return -1;
          }
          return sort === 'asc' ? leftValue - rightValue : rightValue - leftValue;
        });
        categories = order.map((index) => categories[index]);
        series = series.map((item) => ({
          name: item.name,
          values: order.map((index) => {
            const value = item.values[index];
            return value === undefined ? null : value;
          }),
        }));
      }
      return { categories, series };
    },

    drawChart() {
      const spec = this.data.spec as ChartSpec | null;
      if (!spec) {
        return;
      }
      wx.createSelectorQuery()
        .in(this)
        .select('#chartCanvas')
        .fields({ node: true, size: true })
        .exec((result) => {
          const first = result && result[0]
            ? (result[0] as { node?: ICanvasNode; width?: number; height?: number })
            : null;
          if (!first || !first.node) {
            this.setData({ fallbackNote: '图表画布暂不可用，可切换到表格查看。' });
            return;
          }
          const canvas = first.node;
          const width = first.width && first.width > 0 ? first.width : 320;
          const height = first.height && first.height > 0 ? first.height : this.data.canvasHeight;
          let pixelRatio = 2;
          try {
            pixelRatio = wx.getWindowInfo().pixelRatio || 2;
          } catch (error) {
            pixelRatio = 2;
          }
          canvas.width = Math.round(width * pixelRatio);
          canvas.height = Math.round(height * pixelRatio);
          const ctx = canvas.getContext('2d');
          ctx.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
          ctx.clearRect(0, 0, width, height);

          try {
            if (spec.type === 'bar') {
              this.drawBar(ctx, spec, width, height);
            } else if (spec.type === 'hbar') {
              this.drawHBar(ctx, spec, width, height);
            } else if (spec.type === 'line') {
              this.drawLine(ctx, spec, width, height);
            } else if (spec.type === 'pie') {
              this.drawPie(ctx, spec, width, height);
            }
          } catch (error) {
            console.warn('[chart] draw failed', error);
            this.setData({
              mode: 'table',
              manualTable: true,
              fallbackNote: '图表渲染失败，已切换为表格。',
            });
          }
        });
    },

    drawBar(ctx: ICanvas2DContext, spec: ChartSpec, width: number, height: number) {
      const dataset = this.prepareDataset(spec);
      const categories = dataset.categories;
      const series = dataset.series;
      if (!categories.length || !series.length) {
        return;
      }
      const padding = { left: 46, right: 16, top: 18, bottom: 40 };
      const plotWidth = Math.max(20, width - padding.left - padding.right);
      const plotHeight = Math.max(20, height - padding.top - padding.bottom);
      const range = valueRange(collectValues(spec));
      const scaleY = (value: number) =>
        padding.top + ((range.max - value) / (range.max - range.min)) * plotHeight;

      drawGrid(ctx, width, height, padding, plotWidth, plotHeight, range);

      const groupWidth = plotWidth / categories.length;
      const availableBar = Math.max(6, groupWidth * 0.66);
      const barWidth = Math.max(3, Math.min(26, availableBar / series.length));
      const baseline = scaleY(0);
      const showValues = !!(spec.options && spec.options.show_values) && categories.length <= 8;
      const precision = detectSeriesPrecision(series);
      const labelStep = Math.ceil(categories.length / 7);

      categories.forEach((category, categoryIndex) => {
        const centerX = padding.left + groupWidth * categoryIndex + groupWidth / 2;
        series.forEach((item, seriesIndex) => {
          const value = item.values[categoryIndex];
          if (value === null || value === undefined) {
            return;
          }
          const x = centerX - (series.length * barWidth) / 2 + seriesIndex * barWidth;
          const y = scaleY(value);
          const top = Math.min(y, baseline);
          const barHeight = Math.max(1, Math.abs(y - baseline));
          ctx.fillStyle = COLORS[seriesIndex % COLORS.length];
          ctx.fillRect(x + 1, top, Math.max(2, barWidth - 2), barHeight);
          if (showValues) {
            ctx.fillStyle = AXIS_COLOR;
            ctx.font = '10px sans-serif';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'bottom';
            ctx.fillText(formatNumber(value, precision), x + barWidth / 2, top - 3);
          }
        });
        if (categoryIndex % labelStep === 0) {
          ctx.fillStyle = AXIS_COLOR;
          ctx.font = '10px sans-serif';
          ctx.textAlign = 'center';
          ctx.textBaseline = 'top';
          ctx.fillText(truncate(category, 6), centerX, height - padding.bottom + 10);
        }
      });
    },

    drawHBar(ctx: ICanvas2DContext, spec: ChartSpec, width: number, height: number) {
      const dataset = this.prepareDataset(spec);
      const categories = dataset.categories;
      const series = dataset.series;
      if (!categories.length || !series.length) {
        return;
      }
      const padding = { left: 92, right: 48, top: 12, bottom: 14 };
      const plotWidth = Math.max(20, width - padding.left - padding.right);
      const plotHeight = Math.max(20, height - padding.top - padding.bottom);
      const values = collectValues(spec);
      const maxValue = Math.max(0, ...values);
      const safeMax = maxValue > 0 ? maxValue : 1;
      const rowHeight = plotHeight / categories.length;
      const barHeight = Math.max(8, Math.min(26, rowHeight * 0.56));
      const precision = detectSeriesPrecision(series);

      ctx.strokeStyle = GRID_COLOR;
      ctx.lineWidth = 1;
      [0, 0.25, 0.5, 0.75, 1].forEach((ratio) => {
        const x = padding.left + plotWidth * ratio;
        ctx.beginPath();
        ctx.moveTo(x, padding.top);
        ctx.lineTo(x, height - padding.bottom);
        ctx.stroke();
      });

      categories.forEach((category, index) => {
        const y = padding.top + rowHeight * index + rowHeight / 2;
        ctx.fillStyle = AXIS_COLOR;
        ctx.font = '11px sans-serif';
        ctx.textAlign = 'right';
        ctx.textBaseline = 'middle';
        ctx.fillText(truncate(category, 6), padding.left - 8, y);

        const value = series[0].values[index];
        if (value === null || value === undefined) {
          ctx.fillStyle = '#6b7280';
          ctx.font = '10px sans-serif';
          ctx.textAlign = 'left';
          ctx.fillText(EMPTY_CELL, padding.left + 4, y);
          return;
        }
        const barWidth = Math.max(1, (Math.max(0, value) / safeMax) * plotWidth);
        ctx.fillStyle = COLORS[0];
        ctx.fillRect(padding.left, y - barHeight / 2, barWidth, barHeight);
        ctx.fillStyle = AXIS_COLOR;
        ctx.font = '11px sans-serif';
        ctx.textAlign = 'left';
        ctx.textBaseline = 'middle';
        ctx.fillText(
          `${formatNumber(value, precision)}${spec.unit ? ` ${spec.unit}` : ''}`,
          padding.left + barWidth + 6,
          y
        );
      });
    },

    drawLine(ctx: ICanvas2DContext, spec: ChartSpec, width: number, height: number) {
      const dataset = this.prepareDataset(spec);
      const categories = dataset.categories;
      const series = dataset.series;
      if (!categories.length || !series.length) {
        return;
      }
      const padding = { left: 46, right: 16, top: 18, bottom: 40 };
      const plotWidth = Math.max(20, width - padding.left - padding.right);
      const plotHeight = Math.max(20, height - padding.top - padding.bottom);
      const range = valueRange(collectValues(spec));
      const scaleY = (value: number) =>
        padding.top + ((range.max - value) / (range.max - range.min)) * plotHeight;
      const scaleX = (index: number) =>
        categories.length === 1
          ? padding.left + plotWidth / 2
          : padding.left + (plotWidth * index) / (categories.length - 1);
      const precision = detectSeriesPrecision(series);

      drawGrid(ctx, width, height, padding, plotWidth, plotHeight, range);

      series.forEach((item, seriesIndex) => {
        const color = COLORS[seriesIndex % COLORS.length];
        ctx.strokeStyle = color;
        ctx.lineWidth = 2;
        let pathOpen = false;
        item.values.forEach((value, index) => {
          if (value === null || value === undefined) {
            if (pathOpen) {
              ctx.stroke();
              pathOpen = false;
            }
            return;
          }
          const x = scaleX(index);
          const y = scaleY(value);
          if (!pathOpen) {
            ctx.beginPath();
            ctx.moveTo(x, y);
            pathOpen = true;
          } else {
            ctx.lineTo(x, y);
          }
        });
        if (pathOpen) {
          ctx.stroke();
        }
        item.values.forEach((value, index) => {
          if (value === null || value === undefined) {
            return;
          }
          const x = scaleX(index);
          const y = scaleY(value);
          ctx.fillStyle = color;
          ctx.beginPath();
          ctx.arc(x, y, 3, 0, Math.PI * 2);
          ctx.fill();
          if (categories.length <= 6) {
            ctx.fillStyle = AXIS_COLOR;
            ctx.font = '10px sans-serif';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'bottom';
            ctx.fillText(formatNumber(value, precision), x, y - 6);
          }
        });
      });

      const labelStep = Math.ceil(categories.length / 7);
      categories.forEach((category, index) => {
        if (index % labelStep !== 0) {
          return;
        }
        ctx.fillStyle = AXIS_COLOR;
        ctx.font = '10px sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'top';
        ctx.fillText(truncate(category, 7), scaleX(index), height - padding.bottom + 10);
      });
    },

    drawPie(ctx: ICanvas2DContext, spec: ChartSpec, width: number, height: number) {
      const dataset = this.prepareDataset(spec);
      const categories = dataset.categories;
      const values = dataset.series.length ? dataset.series[0].values : [];
      const slices = categories
        .map((category, index) => {
          const value = values[index];
          return {
            category,
            value: value === null || value === undefined ? 0 : Math.max(0, value),
          };
        })
        .filter((item) => item.value > 0);
      const total = slices.reduce((sum, item) => sum + item.value, 0);
      if (!slices.length || total <= 0) {
        return;
      }
      const centerX = width * 0.36;
      const centerY = height * 0.5 + 4;
      const radius = Math.max(30, Math.min(width * 0.28, height * 0.36));
      let start = -Math.PI / 2;
      slices.forEach((slice, index) => {
        const angle = (slice.value / total) * Math.PI * 2;
        ctx.fillStyle = COLORS[index % COLORS.length];
        ctx.beginPath();
        ctx.moveTo(centerX, centerY);
        ctx.arc(centerX, centerY, radius, start, start + angle);
        ctx.closePath();
        ctx.fill();
        start += angle;
      });

      const legendX = width * 0.66;
      let legendY = Math.max(16, centerY - (Math.min(slices.length, 8) * 22) / 2);
      slices.slice(0, 8).forEach((slice, index) => {
        ctx.fillStyle = COLORS[index % COLORS.length];
        ctx.fillRect(legendX, legendY + 2, 8, 8);
        ctx.fillStyle = AXIS_COLOR;
        ctx.font = '10px sans-serif';
        ctx.textAlign = 'left';
        ctx.textBaseline = 'top';
        const percent = ((slice.value / total) * 100).toFixed(1);
        ctx.fillText(`${truncate(slice.category, 8)} ${percent}%`, legendX + 14, legendY);
        legendY += 22;
      });
    },
  },
});

function collectValues(spec: ChartSpec): number[] {
  const values: number[] = [];
  (spec.series || []).forEach((item) => {
    item.values.forEach((value) => {
      if (typeof value === 'number' && Number.isFinite(value)) {
        values.push(value);
      }
    });
  });
  (spec.rows || []).forEach((row) => {
    row.forEach((cell) => {
      if (typeof cell === 'number' && Number.isFinite(cell)) {
        values.push(cell);
      }
    });
  });
  return values;
}

function valueRange(values: number[]): { min: number; max: number } {
  if (!values.length) {
    return { min: 0, max: 1 };
  }
  let min = Math.min(0, ...values);
  let max = Math.max(0, ...values);
  if (min === max) {
    max += 1;
    min -= 1;
  }
  return { min, max };
}

function detectSeriesPrecision(series: ChartSeries[]): number {
  const values = series.reduce<number[]>((all, item) => {
    item.values.forEach((value) => {
      if (typeof value === 'number' && Number.isFinite(value)) {
        all.push(value);
      }
    });
    return all;
  }, []);
  if (!values.length) {
    return 0;
  }
  return values.every((value) => Number.isInteger(value)) ? 0 : 2;
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

function formatCell(cell: string | number | null | undefined, precision: number): string {
  if (cell === null || cell === undefined || cell === '') {
    return EMPTY_CELL;
  }
  if (typeof cell === 'number') {
    return formatNumber(cell, precision);
  }
  return cell;
}

function drawGrid(
  ctx: ICanvas2DContext,
  width: number,
  height: number,
  padding: { left: number; right: number; top: number; bottom: number },
  plotWidth: number,
  plotHeight: number,
  range: { min: number; max: number }
): void {
  const steps = 4;
  ctx.lineWidth = 1;
  ctx.font = '10px sans-serif';
  ctx.textAlign = 'right';
  ctx.textBaseline = 'middle';
  for (let index = 0; index <= steps; index += 1) {
    const ratio = index / steps;
    const value = range.max - (range.max - range.min) * ratio;
    const y = padding.top + plotHeight * ratio;
    ctx.strokeStyle = GRID_COLOR;
    ctx.beginPath();
    ctx.moveTo(padding.left, y);
    ctx.lineTo(padding.left + plotWidth, y);
    ctx.stroke();
    ctx.fillStyle = AXIS_COLOR;
    ctx.fillText(formatAxisValue(value, range), padding.left - 6, y);
  }
  const zeroY = padding.top + ((range.max - 0) / (range.max - range.min)) * plotHeight;
  ctx.strokeStyle = '#c7d1dc';
  ctx.beginPath();
  ctx.moveTo(padding.left, zeroY);
  ctx.lineTo(padding.left + plotWidth, zeroY);
  ctx.stroke();
}

function formatAxisValue(value: number, range: { min: number; max: number }): string {
  const span = Math.abs(range.max - range.min);
  if (span >= 100) {
    return formatNumber(value, 0);
  }
  if (span >= 10) {
    return formatNumber(value, 1);
  }
  return formatNumber(value, 2);
}
