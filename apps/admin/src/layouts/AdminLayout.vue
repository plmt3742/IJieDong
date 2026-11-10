<script setup lang="ts">
import {
  DataBoard,
  Expand,
  Files,
  Fold,
  Setting,
  Stamp,
} from '@element-plus/icons-vue'
import { ElMessageBox } from 'element-plus'
import { computed, onBeforeUnmount, onMounted, ref, type Component } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import type { Role } from '@/api/types'
import { useAuthStore } from '@/stores/auth'
import { ROLE_LABELS } from '@/utils/format'

interface NavLeaf {
  index: string
  title: string
  roles?: Role[]
}

interface NavGroup {
  key: string
  title: string
  icon: Component
  children: NavLeaf[]
}

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()

const navGroups: NavGroup[] = [
  {
    key: 'data',
    title: '数据管理',
    icon: Files,
    children: [
      { index: '/data', title: '数据列表', roles: ['viewer', 'editor', 'admin', 'approver'] },
      { index: '/import', title: '数据导入', roles: ['editor', 'admin'] },
    ],
  },
  {
    key: 'permission',
    title: '权限管理',
    icon: Stamp,
    children: [
      { index: '/applications', title: '申请审批', roles: ['admin', 'approver'] },
      { index: '/users', title: '用户管理', roles: ['admin'] },
      { index: '/audit', title: '审计日志', roles: ['admin'] },
    ],
  },
  {
    key: 'system',
    title: '系统',
    icon: Setting,
    children: [
      { index: '/ai-logs', title: '问答记录' },
      { index: '/components', title: '组件库' },
      { index: '/settings', title: '设置' },
    ],
  },
]

const visibleGroups = computed<NavGroup[]>(() =>
  navGroups
    .map((group) => ({
      ...group,
      children: group.children.filter((leaf) => auth.hasRole(leaf.roles)),
    }))
    .filter((group) => group.children.length > 0),
)

const activeMenu = computed(() => route.path)

const collapsed = ref(false)
let mediaQuery: MediaQueryList | null = null

function applyViewport(event?: MediaQueryList | MediaQueryListEvent): void {
  const target = event ?? mediaQuery
  if (!target) return
  collapsed.value = target.matches
}

function toggleSidebar(): void {
  collapsed.value = !collapsed.value
}

onMounted(() => {
  mediaQuery = window.matchMedia('(max-width: 1180px)')
  applyViewport(mediaQuery)
  mediaQuery.addEventListener('change', applyViewport)
})

onBeforeUnmount(() => {
  mediaQuery?.removeEventListener('change', applyViewport)
})

const roleLabel = computed(() => {
  const role = auth.user?.role
  return role ? (ROLE_LABELS[role] ?? role) : '未登录'
})

async function handleSignOut(): Promise<void> {
  try {
    await ElMessageBox.confirm('退出后需要重新登录才能访问管理后台。', '确认退出登录', {
      confirmButtonText: '退出登录',
      cancelButtonText: '取消',
      type: 'warning',
    })
  } catch {
    return
  }
  await auth.signOut({ notifyServer: true })
  await router.replace({ path: '/login' })
}
</script>

<template>
  <div class="admin-shell" :class="{ 'is-collapsed': collapsed }">
    <aside class="admin-aside">
      <div class="brand">
        <span class="brand__mark" aria-hidden="true">i</span>
        <span v-if="!collapsed" class="brand__text">
          <strong>i揭东</strong>
          <span>数据管理后台</span>
        </span>
      </div>

      <el-menu
        class="admin-menu"
        :default-active="activeMenu"
        :collapse="collapsed"
        :collapse-transition="false"
        router
      >
        <el-menu-item index="/overview">
          <el-icon><DataBoard /></el-icon>
          <template #title>总览</template>
        </el-menu-item>

        <el-sub-menu v-for="group in visibleGroups" :key="group.key" :index="group.key">
          <template #title>
            <el-icon><component :is="group.icon" /></el-icon>
            <span>{{ group.title }}</span>
          </template>
          <el-menu-item v-for="leaf in group.children" :key="leaf.index" :index="leaf.index">
            <span>{{ leaf.title }}</span>
          </el-menu-item>
        </el-sub-menu>
      </el-menu>

      <div v-if="!collapsed" class="aside-foot">
        <span class="aside-foot__label">数据口径</span>
        <span class="aside-foot__value">合成演示数据，仅用于 B05 演示</span>
      </div>
    </aside>

    <div class="admin-main">
      <header class="admin-header">
        <div class="admin-header__left">
          <button
            type="button"
            class="header-toggle"
            :aria-label="collapsed ? '展开导航' : '收起导航'"
            @click="toggleSidebar"
          >
            <el-icon><component :is="collapsed ? Expand : Fold" /></el-icon>
          </button>
          <el-tag size="small" effect="plain" type="info">演示环境 Demo v0</el-tag>
          <el-tag size="small" effect="plain" type="warning">演示数据</el-tag>
          <span class="admin-header__title">{{ route.meta.title }}</span>
        </div>

        <div class="admin-header__right">
          <span class="admin-header__name">{{ auth.user?.display_name ?? '未登录' }}</span>
          <el-tag size="small" effect="plain">{{ roleLabel }}</el-tag>
          <span v-if="auth.user?.unit" class="admin-header__unit">{{ auth.user.unit }}</span>
          <el-button text type="primary" @click="handleSignOut">退出登录</el-button>
        </div>
      </header>

      <main class="admin-content">
        <RouterView />
      </main>
    </div>
  </div>
</template>

<style scoped>
.admin-shell {
  display: flex;
  min-height: 100vh;
  background: var(--gov-bg);
}

.admin-aside {
  position: sticky;
  top: 0;
  display: flex;
  flex-direction: column;
  width: var(--gov-sidebar-width);
  height: 100vh;
  flex: 0 0 auto;
  background: var(--gov-surface);
  border-right: 1px solid var(--gov-border);
  transition: width 120ms ease-out;
  overflow: hidden;
}

.admin-shell.is-collapsed .admin-aside {
  width: var(--gov-sidebar-collapsed);
}

.brand {
  display: flex;
  align-items: center;
  gap: var(--gov-space-3);
  height: var(--gov-header-height);
  padding: 0 var(--gov-space-4);
  border-bottom: 1px solid var(--gov-border);
  flex: 0 0 auto;
}

.brand__mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  flex: 0 0 auto;
  border-radius: var(--gov-radius-sm);
  background: var(--gov-primary);
  color: var(--gov-text-inverse);
  font-weight: 700;
  font-size: var(--gov-text-lg);
  line-height: 1;
}

.brand__text {
  display: flex;
  flex-direction: column;
  line-height: var(--gov-line-tight);
  white-space: nowrap;
}

.brand__text strong {
  font-size: var(--gov-text-lg);
  color: var(--gov-text);
}

.brand__text span {
  font-size: var(--gov-text-xs);
  color: var(--gov-text-muted);
}

.admin-menu {
  flex: 1 1 auto;
  border-right: none;
  padding-top: var(--gov-space-2);
  overflow-y: auto;
}

.admin-menu:not(.el-menu--collapse) {
  width: 100%;
}

.aside-foot {
  flex: 0 0 auto;
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: var(--gov-space-3) var(--gov-space-4);
  border-top: 1px solid var(--gov-border);
  background: var(--gov-surface-muted);
}

.aside-foot__label {
  font-size: var(--gov-text-xs);
  color: var(--gov-text-muted);
}

.aside-foot__value {
  font-size: var(--gov-text-xs);
  color: var(--gov-text-secondary);
}

.admin-main {
  display: flex;
  flex-direction: column;
  flex: 1 1 auto;
  min-width: 0;
}

.admin-header {
  position: sticky;
  top: 0;
  z-index: 10;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--gov-space-4);
  height: var(--gov-header-height);
  padding: 0 var(--gov-space-4);
  background: var(--gov-surface);
  border-bottom: 1px solid var(--gov-border);
}

.admin-header__left,
.admin-header__right {
  display: flex;
  align-items: center;
  gap: var(--gov-space-2);
  min-width: 0;
}

.admin-header__title {
  margin-left: var(--gov-space-2);
  font-size: var(--gov-text-base);
  font-weight: 600;
  color: var(--gov-text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.admin-header__name {
  font-size: var(--gov-text-sm);
  color: var(--gov-text);
  white-space: nowrap;
}

.admin-header__unit {
  font-size: var(--gov-text-xs);
  color: var(--gov-text-muted);
  white-space: nowrap;
  max-width: 160px;
  overflow: hidden;
  text-overflow: ellipsis;
}

.header-toggle {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  padding: 0;
  border: 1px solid var(--gov-border);
  border-radius: var(--gov-radius-sm);
  background: var(--gov-surface);
  color: var(--gov-text-secondary);
  cursor: pointer;
}

.header-toggle:hover {
  border-color: var(--gov-border-strong);
  color: var(--gov-text);
}

.admin-content {
  flex: 1 1 auto;
  padding: var(--gov-space-5) var(--gov-space-6) var(--gov-space-8);
  min-width: 0;
}

@media (max-width: 1180px) {
  .admin-content {
    padding: var(--gov-space-4);
  }

  .admin-header__unit {
    display: none;
  }
}

@media (max-width: 820px) {
  .admin-header__title {
    display: none;
  }

  .admin-header {
    flex-wrap: nowrap;
  }
}
</style>
