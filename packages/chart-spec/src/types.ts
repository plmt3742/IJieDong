export const CHART_SPEC_VERSION = "1.0" as const;

export type ChartType = "bar" | "hbar" | "line" | "pie" | "table";

export interface ChartSeries {
  name: string;
  values: Array<number | null>;
}

export interface TableColumn {
  key: string;
  label: string;
  align?: "left" | "center" | "right";
}

export interface ChartSpec {
  version: typeof CHART_SPEC_VERSION;
  type: ChartType;
  title: string;
  subtitle?: string;
  unit?: string;
  categories?: string[];
  series?: ChartSeries[];
  columns?: TableColumn[];
  rows?: Array<Array<string | number | null>>;
  options?: {
    show_values?: boolean;
    sort?: "none" | "asc" | "desc";
    max_items?: number;
  };
}

export interface ValidationIssue {
  path: string;
  message: string;
}

export type EChartsOption = Record<string, unknown>;
