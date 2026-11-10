import { assertChartSpec } from "./schema.js";
import type { ChartSpec, EChartsOption } from "./types.js";

const PIE_OTHER = "其他";

function mergePieCategories(spec: ChartSpec): ChartSpec {
  const maxItems = spec.options?.max_items ?? 8;
  const categories = spec.categories ?? [];
  if (categories.length <= maxItems) {
    return spec;
  }

  const firstSeries = spec.series?.[0];
  const items = categories.map((name, index) => ({
    name,
    value: firstSeries?.values[index] ?? 0,
  }));
  const sorted = [...items].sort((left, right) => Number(right.value ?? 0) - Number(left.value ?? 0));
  const kept = sorted.slice(0, Math.max(1, maxItems - 1));
  const other = sorted.slice(Math.max(1, maxItems - 1)).reduce((sum, item) => sum + Number(item.value ?? 0), 0);

  return {
    ...spec,
    categories: [...kept.map((item) => item.name), PIE_OTHER],
    series: [
      {
        name: firstSeries?.name ?? "数值",
        values: [...kept.map((item) => item.value), other],
      },
    ],
  };
}

export function toEChartsOption(spec: ChartSpec): EChartsOption {
  assertChartSpec(spec);
  if (spec.type === "table") {
    return {
      type: "table",
      columns: spec.columns ?? [],
      rows: spec.rows ?? [],
    };
  }

  const normalized = spec.type === "pie" ? mergePieCategories(spec) : spec;
  const categories = normalized.categories ?? [];
  const series = normalized.series ?? [];
  const unitSuffix = spec.unit ? ` (${spec.unit})` : "";

  if (spec.type === "pie") {
    const values = series[0]?.values ?? [];
    return {
      title: { text: spec.title, subtext: spec.subtitle },
      tooltip: { trigger: "item" },
      legend: { bottom: 0 },
      series: [
        {
          type: "pie",
          radius: ["35%", "65%"],
          data: categories.map((name, index) => ({
            name,
            value: values[index] ?? null,
          })),
        },
      ],
    };
  }

  return {
    title: { text: spec.title, subtext: spec.subtitle },
    tooltip: { trigger: "axis" },
    grid: { left: 16, right: 24, top: 48, bottom: 32, containLabel: true },
    xAxis:
      spec.type === "hbar"
        ? { type: "value", name: unitSuffix }
        : { type: "category", data: categories, axisLabel: { interval: 0, rotate: categories.length > 8 ? 30 : 0 } },
    yAxis:
      spec.type === "hbar"
        ? { type: "category", data: categories }
        : { type: "value", name: unitSuffix },
    series: series.map((item) => ({
      name: item.name,
      type: spec.type === "hbar" ? "bar" : spec.type,
      data: item.values,
      connectNulls: false,
      label: { show: spec.options?.show_values ?? false, position: "top" },
    })),
  };
}
