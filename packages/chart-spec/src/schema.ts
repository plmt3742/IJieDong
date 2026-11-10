import {
  CHART_SPEC_VERSION,
  type ChartSpec,
  type ValidationIssue,
} from "./types.js";

const CHART_TYPES = new Set(["bar", "hbar", "line", "pie", "table"]);

export function validateChartSpec(spec: unknown): ValidationIssue[] {
  const issues: ValidationIssue[] = [];
  if (!spec || typeof spec !== "object") {
    return [{ path: "$", message: "ChartSpec must be an object" }];
  }

  const candidate = spec as Partial<ChartSpec>;
  if (candidate.version !== CHART_SPEC_VERSION) {
    issues.push({ path: "$.version", message: `version must be ${CHART_SPEC_VERSION}` });
  }
  if (!candidate.type || !CHART_TYPES.has(candidate.type)) {
    issues.push({ path: "$.type", message: "type must be bar, hbar, line, pie, or table" });
  }
  if (!candidate.title || typeof candidate.title !== "string") {
    issues.push({ path: "$.title", message: "title is required" });
  }

  if (candidate.type === "table") {
    if (!Array.isArray(candidate.columns) || candidate.columns.length === 0) {
      issues.push({ path: "$.columns", message: "table requires at least one column" });
    }
    if (!Array.isArray(candidate.rows)) {
      issues.push({ path: "$.rows", message: "table requires rows" });
    }
    return issues;
  }

  if (!Array.isArray(candidate.categories) || candidate.categories.length === 0) {
    issues.push({ path: "$.categories", message: "chart requires categories" });
  }
  if (!Array.isArray(candidate.series) || candidate.series.length === 0) {
    issues.push({ path: "$.series", message: "chart requires at least one series" });
    return issues;
  }

  const categoryCount = candidate.categories?.length ?? 0;
  candidate.series.forEach((series, index) => {
    if (!Array.isArray(series.values)) {
      issues.push({ path: `$.series[${index}].values`, message: "values must be an array" });
      return;
    }
    if (series.values.length !== categoryCount) {
      issues.push({
        path: `$.series[${index}].values`,
        message: "values length must equal categories length",
      });
    }
    if (series.values.some((value) => value !== null && !Number.isFinite(value))) {
      issues.push({
        path: `$.series[${index}].values`,
        message: "values must be finite numbers or null",
      });
    }
  });

  return issues;
}

export function assertChartSpec(spec: unknown): asserts spec is ChartSpec {
  const issues = validateChartSpec(spec);
  if (issues.length > 0) {
    throw new Error(issues.map((issue) => `${issue.path}: ${issue.message}`).join("; "));
  }
}
