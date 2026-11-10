<script setup lang="ts">
import { useRouter } from 'vue-router'

import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()

async function backToOverview(): Promise<void> {
  if (auth.isAuthenticated) {
    await router.replace('/overview')
  } else {
    await router.replace('/login')
  }
}
</script>

<template>
  <div class="state-page">
    <div class="state-page__card panel">
      <p class="state-page__code">403</p>
      <h1 class="state-page__title">当前角色无权访问该页面</h1>
      <p class="state-page__description">
        后台按角色开放功能：数据列表、导入、申请审批、用户与审计的可见范围不同。如需更多权限，请联系管理员调整角色。
      </p>
      <div class="state-page__actions">
        <el-button type="primary" @click="backToOverview">返回总览</el-button>
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
