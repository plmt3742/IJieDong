<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()

function goHome(): void {
  void router.replace('/overview')
}
</script>

<template>
  <div class="state-page">
    <div class="state-page__card panel">
      <p class="state-page__code">404</p>
      <h1 class="state-page__title">页面不存在</h1>
      <p class="state-page__description">
        访问的地址没有对应页面，可能是链接已失效或路径输入有误。
      </p>
      <div class="state-page__actions">
        <el-button type="primary" @click="goHome">返回总览</el-button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.state-page {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  padding: var(--gov-space-6);
  background: var(--gov-bg);
}

.state-page__card {
  max-width: 520px;
  padding: var(--gov-space-8);
  display: flex;
  flex-direction: column;
  gap: var(--gov-space-2);
}

.state-page__code {
  font-family: var(--gov-font-mono);
  font-size: var(--gov-text-sm);
  color: var(--gov-text-muted);
  letter-spacing: 0.12em;
}

.state-page__title {
  font-size: var(--gov-text-xl);
  font-weight: 600;
  line-height: var(--gov-line-tight);
}

.state-page__description {
  color: var(--gov-text-secondary);
  font-size: var(--gov-text-sm);
  line-height: 1.7;
}

.state-page__actions {
  margin-top: var(--gov-space-3);
}
</style>
