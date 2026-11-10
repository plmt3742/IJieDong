<script setup lang="ts">
interface Props {
  label: string
  value: number | null
  unit: string
}

const props = defineProps<Props>()

function display(value: number | null): string {
  if (value === null) return '暂无数据'
  return new Intl.NumberFormat('zh-CN', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  }).format(value)
}

const isMissing = (): boolean => props.value === null
</script>

<template>
  <article class="metric-card panel" :data-missing="isMissing()">
    <p class="metric-card__label">{{ label }}</p>
    <p class="metric-card__value">
      <span v-if="!isMissing()">{{ display(value) }}</span>
      <span v-else class="metric-card__empty">暂无数据</span>
      <span v-if="!isMissing() && unit" class="metric-card__unit">{{ unit }}</span>
    </p>
  </article>
</template>

<style scoped>
.metric-card {
  display: flex;
  flex-direction: column;
  gap: var(--gov-space-1);
  padding: var(--gov-space-4);
  min-width: 0;
}

.metric-card__label {
  font-size: var(--gov-text-sm);
  color: var(--gov-text-secondary);
}

.metric-card__value {
  display: flex;
  align-items: baseline;
  gap: 6px;
  font-size: var(--gov-text-2xl);
  font-weight: 600;
  line-height: var(--gov-line-tight);
  color: var(--gov-text);
  font-variant-numeric: tabular-nums;
  word-break: break-word;
}

.metric-card__unit {
  font-size: var(--gov-text-sm);
  font-weight: 400;
  color: var(--gov-text-muted);
}

.metric-card__empty {
  font-size: var(--gov-text-lg);
  font-weight: 500;
  color: var(--gov-text-muted);
}

.metric-card__note {
  font-size: var(--gov-text-xs);
  color: var(--gov-text-muted);
}

.metric-card[data-missing="true"] {
  background: var(--gov-surface-muted);
}
</style>
