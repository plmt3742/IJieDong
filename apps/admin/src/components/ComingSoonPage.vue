<script setup lang="ts">
interface Props {
  code: string
  title: string
  description: string
  planned: string[]
}

defineProps<Props>()
</script>

<template>
  <div class="page">
    <div class="coming-soon panel">
      <p class="coming-soon__code">{{ code }}</p>
      <h1 class="coming-soon__title">{{ title }}</h1>
      <p class="coming-soon__status">B05 未实现</p>
      <p class="coming-soon__description">{{ description }}</p>

      <div class="coming-soon__planned">
        <p class="coming-soon__planned-label">计划交付内容</p>
        <ul class="coming-soon__list">
          <li v-for="item in planned" :key="item">{{ item }}</li>
        </ul>
      </div>

      <p class="coming-soon__note">
        本页面不展示任何模拟数据，避免把未实现的接口误认为已接通。
      </p>
    </div>
  </div>
</template>

<style scoped>
.coming-soon {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: var(--gov-space-2);
  padding: var(--gov-space-8);
  max-width: 720px;
}

.coming-soon__code {
  font-family: var(--gov-font-mono);
  font-size: var(--gov-text-xs);
  color: var(--gov-text-muted);
  letter-spacing: 0.08em;
}

.coming-soon__title {
  font-size: var(--gov-text-xl);
  font-weight: 600;
  line-height: var(--gov-line-tight);
}

.coming-soon__status {
  display: inline-block;
  padding: 2px var(--gov-space-2);
  border: 1px solid var(--gov-border-strong);
  border-radius: var(--gov-radius-sm);
  background: var(--gov-surface-sunken);
  color: var(--gov-text-secondary);
  font-size: var(--gov-text-xs);
}

.coming-soon__description {
  margin-top: var(--gov-space-1);
  color: var(--gov-text-secondary);
  font-size: var(--gov-text-sm);
  max-width: 60ch;
}

.coming-soon__planned {
  margin-top: var(--gov-space-3);
  padding-top: var(--gov-space-3);
  border-top: 1px solid var(--gov-border);
  width: 100%;
}

.coming-soon__planned-label {
  font-size: var(--gov-text-sm);
  color: var(--gov-text);
  font-weight: 600;
}

.coming-soon__list {
  margin: var(--gov-space-2) 0 0;
  padding-left: var(--gov-space-5);
  color: var(--gov-text-secondary);
  font-size: var(--gov-text-sm);
}

.coming-soon__list li {
  margin-bottom: var(--gov-space-1);
}

.coming-soon__note {
  margin-top: var(--gov-space-3);
  color: var(--gov-text-muted);
  font-size: var(--gov-text-xs);
}
</style>
