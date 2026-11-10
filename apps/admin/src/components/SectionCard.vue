<script setup lang="ts">
interface Props {
  title: string
  hint?: string
  flush?: boolean
}

defineProps<Props>()
</script>

<template>
  <section class="section-card panel">
    <header class="section-card__header">
      <div class="section-card__heading">
        <h2 class="panel__title">{{ title }}</h2>
        <p v-if="hint" class="panel__hint">{{ hint }}</p>
      </div>
      <div v-if="$slots.extra" class="section-card__extra">
        <slot name="extra" />
      </div>
    </header>
    <div :class="flush ? '' : 'section-card__body'">
      <slot />
    </div>
    <footer v-if="$slots.footer" class="section-card__footer">
      <slot name="footer" />
    </footer>
  </section>
</template>

<style scoped>
.section-card {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.section-card__header {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--gov-space-2);
  padding: var(--gov-space-3) var(--gov-space-4);
  border-bottom: 1px solid var(--gov-border);
}

.section-card__heading {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.section-card__extra {
  display: flex;
  align-items: center;
  gap: var(--gov-space-2);
}

.section-card__body {
  padding: var(--gov-space-4);
}

.section-card__footer {
  padding: var(--gov-space-3) var(--gov-space-4);
  border-top: 1px solid var(--gov-border);
}
</style>
