<script setup lang="ts">
interface Props {
  title: string
  description?: string
}

defineProps<Props>()
</script>

<template>
  <div class="page-header">
    <div class="page-header__text">
      <h1 class="page-header__title">{{ title }}</h1>
      <p v-if="description" class="page-header__description">{{ description }}</p>
    </div>
    <div v-if="$slots.actions" class="page-header__actions">
      <slot name="actions" />
    </div>
  </div>
</template>

<style scoped>
.page-header {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--gov-space-3);
}

.page-header__text {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.page-header__title {
  font-size: var(--gov-text-xl);
  font-weight: 600;
  line-height: var(--gov-line-tight);
  color: var(--gov-text);
}

.page-header__description {
  font-size: var(--gov-text-sm);
  color: var(--gov-text-secondary);
  max-width: 980px;
  line-height: 1.7;
}

.page-header__actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--gov-space-2);
}
</style>
