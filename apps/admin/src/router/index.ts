import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'

import { useAuthStore } from '@/stores/auth'
import type { Role } from '@/api/types'

declare module 'vue-router' {
  interface RouteMeta {
    title?: string
    public?: boolean
    roles?: Role[]
  }
}

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/LoginView.vue'),
    meta: { title: '登录', public: true },
  },
  {
    path: '/',
    component: () => import('@/layouts/AdminLayout.vue'),
    redirect: '/overview',
    children: [
      {
        path: 'overview',
        name: 'overview',
        component: () => import('@/views/OverviewView.vue'),
        meta: { title: '总览' },
      },
      {
        path: 'data',
        name: 'data',
        component: () => import('@/views/DataListView.vue'),
        meta: { title: '数据列表', roles: ['viewer', 'editor', 'admin', 'approver'] },
      },
      {
        path: 'import',
        name: 'import',
        component: () => import('@/views/ImportView.vue'),
        meta: { title: '导入', roles: ['editor', 'admin'] },
      },
      {
        path: 'applications',
        name: 'applications',
        component: () => import('@/views/ApplicationsView.vue'),
        meta: { title: '申请审批', roles: ['admin', 'approver'] },
      },
      {
        path: 'users',
        name: 'users',
        component: () => import('@/views/UsersView.vue'),
        meta: { title: '用户管理', roles: ['admin'] },
      },
      {
        path: 'audit',
        name: 'audit',
        component: () => import('@/views/AuditView.vue'),
        meta: { title: '审计日志', roles: ['admin'] },
      },
      {
        path: 'ai-logs',
        name: 'ai-logs',
        component: () => import('@/views/AiLogsView.vue'),
        meta: { title: '问答记录' },
      },
      {
        path: 'components',
        name: 'components',
        component: () => import('@/views/ComponentsView.vue'),
        meta: { title: '组件库' },
      },
      {
        path: 'settings',
        name: 'settings',
        component: () => import('@/views/SettingsView.vue'),
        meta: { title: '设置' },
      },
    ],
  },
  {
    path: '/403',
    name: 'forbidden',
    component: () => import('@/views/ForbiddenView.vue'),
    meta: { title: '无权限' },
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'not-found',
    component: () => import('@/views/NotFoundView.vue'),
    meta: { title: '页面不存在', public: true },
  },
]

export const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 }),
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()

  if (to.meta.public) {
    if (to.name === 'login' && auth.isAuthenticated) {
      return { path: '/overview' }
    }
    return true
  }

  if (!auth.isAuthenticated) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }

  if (!auth.user) {
    try {
      await auth.loadMe()
    } catch {
      auth.clearSession()
      return { path: '/login', query: { redirect: to.fullPath } }
    }
  }

  if (to.name === 'forbidden') return true

  if (!auth.hasRole(to.meta.roles)) {
    return { name: 'forbidden' }
  }

  return true
})

router.afterEach((to) => {
  const title = to.meta.title ? `${to.meta.title} · i揭东管理后台` : 'i揭东 · 数据管理后台'
  document.title = title
})
