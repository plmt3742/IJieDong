/** ChartSpec contract shared by the API and the canvas renderer. */

export type ChartType = 'bar' | 'hbar' | 'line' | 'pie' | 'table';

export interface ChartSeries {
  name: string;
  values: Array<number | null>;
}

export interface ChartOptions {
  show_values?: boolean;
  sort?: 'none' | 'asc' | 'desc';
  max_items?: number;
}

export interface ChartSpec {
  version: string;
  type: ChartType;
  title: string;
  subtitle?: string | null;
  unit?: string | null;
  categories?: string[];
  series?: ChartSeries[];
  columns?: string[];
  rows?: Array<Array<string | number | null>>;
  options?: ChartOptions;
}

export interface ChartTableModel {
  columns: string[];
  rows: Array<Array<string | number | null>>;
}

export function isChartTable(spec: ChartSpec): boolean {
  return spec.type === 'table' || !!spec.columns;
}
