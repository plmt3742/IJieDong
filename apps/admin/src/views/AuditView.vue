<script setup lang="ts">
import { Refresh, Search } from '@element-plus/icons-vue'
import { computed, onMounted, reactive, ref } from 'vue'

import { listAuditLogs } from '@/api/admin'
import { describeApiError, describeApiErrorDetail } from '@/api/http'
import type { AuditLog } from '@/api/types'
import PageHeader from '@/components/PageHeader.vue'
import SectionCard from '@/components/SectionCard.vue'
import { useRequest } from '@/composables/useRequest'
import { formatDateTime, toRedactedJson } from '@/utils/format'

interface Filters {
  action: string
  userId: number | undefined
  dateRange: [string, string] | null
}

const filters = reactive<Filters>({ action: '', userId: undefined, dateRange: null })
const page = ref(1)
const pageSize = ref(20)

const ACTION_HINTS = [
  'auth.login',
  'application.submit',
  'application.approve',
  'application.reject',
  'user.role_change',
  'user.disable',
  'user.enable',
  'import.create',
  'export.create',
]

const listRequest = useRequest(() =>
  listAuditLogs({
    action: filters.action.trim() || undefined,
    user_id: filters.userId ?? undefined,
    date_from: filters.dateRange?.[0],
    date_to: filters.dateRange?.[1],
    page: page.value,
    page_size: pageSize.value,
  }),
)

const rows = computed<AuditLog[]>(() => listRequest.data.value?.data ?? [])
const total = computed(() => listRequest.data.value?.meta.total ?? 0)

function formatResource(log: AuditLog): string {
  if (!log.resource_type && (log.resource_id === null || log.resource_id === undefined)) return '—'
  const type = log.resource_type ?? '资源'
  if (log.resource_id === null || log.resource_id === undefined) return type
  return `${type} #${log.resource_id}`
}

function formatUser(log: AuditLog): string {
  if (log.user_display_name) return log.user_display_name
  if (log.username) return log.username
  if (typeof log.user_id === 'number') return `用户 #${log.user_id}`
  return '系统'
}

function applyFilters(): void {
  page.value = 1
  void listRequest.run()
}

function resetFilters(): void {
  filters.action = ''
  filters.userId = undefined
  filters.dateRange = null
  page.value = 1
  void listRequest.run()
}

function handlePageChange(next: number): void {
  page.value = next
  void listRequest.run()
}

function handleSizeChange(next: number): void {
  pageSize.value = next
  page.value = 1
  void listRequest.run()
}

/* ---- Detail drawer ---- */

const detailVisible = ref(false)
const activeLog = ref<AuditLog | null>(null)

function openDetail(log: AuditLog): void {
  activeLog.value = log
  detailVisible.value = true
}

const activeDetailJson = computed(() => (activeLog.value ? toRedactedJson(activeLog.value.detail) : ''))

const listErrorText = computed(() =>
  listRequest.error.value ? describeApiError(listRequest.error.value) : '',
)
const listErrorDetail = computed(() =>
  listRequest.error.value ? describeApiErrorDetail(listRequest.error.value) : '',
)

onMounted(() => {
  void listRequest.run()
})
</script>

<template>
  <div class="page">
    <PageHeader
      title="审计日志"
      description="追溯登录、申请审批、角色与状态变更、数据导入与导出。敏感字段在详情中脱敏。"
    >
      <template #actions>
        <el-button :icon="Refresh" @click="listRequest.run()">刷新</el-button>
      </template>
    </PageHeader>

    <SectionCard title="筛选条件" flush>
      <div class="panel__body">
        <div class="filter-row">
          <div class="filter-row__field">
            <span class="filter-row__label">动作</span>
            <el-select
              v-model="filters.action"
              filterable
              allow-create
              clearable
              default-first-option
              placeholder="全部动作"
            >
              <el-option v-for="action in ACTION_HINTS" :key="action" :label="action" :value="action" />
            </el-select>
          </div>
          <div class="filter-row__field filter-row__field--narrow">
            <span class="filter-row__label">用户 ID</span>
            <el-input-number
              v-model="filters.userId"
              :min="1"
              :controls="false"
              placeholder="全部用户"
              style="width: 100%"
            />
          </div>
          <div class="filter-row__field filter-row__field--wide">
            <span class="filter-row__label">时间范围</span>
            <el-date-picker
              v-model="filters.dateRange"
              type="daterange"
              value-format="YYYY-MM-DD"
              start-placeholder="开始日期"
              end-placeholder="结束日期"
              style="width: 100%"
            />
          </div>
          <div class="filter-row__actions">
            <el-button type="primary" :icon="Search" @click="applyFilters">查询</el-button>
            <el-button @click="resetFilters">重置</el-button>
          </div>
        </div>
      </div>
    </SectionCard>

    <el-alert v-if="listRequest.error.value" type="error" show-icon :closable="false">
      <template #title>{{ listErrorText }}</template>
      <template #default>
        <div class="alert-body">
          <span class="alert-body__detail">{{ listErrorDetail }}</span>
          <el-button size="small" @click="listRequest.run()">重试</el-button>
        </div>
      </template>
    </el-alert>

    <SectionCard title="日志记录" :hint="`共 ${total} 条`" flush>
      <el-alert
        v-if="filters.dateRange"
        class="range-hint"
        type="info"
        :closable="false"
        title="Demo v0 审计接口暂未提供时间过滤参数，当前结果未按时间范围裁剪。"
      />
      <el-table
        v-loading="listRequest.loading.value"
        :data="rows"
        stripe
        border
        style="width: 100%"
        empty-text="没有符合条件的审计记录"
      >
        <el-table-column label="时间" width="152">
          <template #default="{ row }">
            {{ formatDateTime((row as AuditLog).created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="用户" min-width="130">
          <template #default="{ row }">{{ formatUser(row as AuditLog) }}</template>
        </el-table-column>
        <el-table-column label="动作" min-width="180">
          <template #default="{ row }">
            <span class="text-mono">{{ (row as AuditLog).action }}</span>
          </template>
        </el-table-column>
        <el-table-column label="资源" min-width="140">
          <template #default="{ row }">{{ formatResource(row as AuditLog) }}</template>
        </el-table-column>
        <el-table-column label="IP" width="130">
          <template #default="{ row }">
            <span class="text-mono">{{ (row as AuditLog).ip ?? '—' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="88" fixed="right" align="center">
          <template #default="{ row }">
            <el-button link type="primary" @click="openDetail(row as AuditLog)">详情</el-button>
          </template>
        </el-table-column>
      </el-table>

      <template #footer>
        <div class="pager">
          <el-pagination
            background
            layout="total, sizes, prev, pager, next"
            :current-page="page"
            :page-size="pageSize"
            :page-sizes="[10, 20, 50, 100]"
            :total="total"
            @current-change="handlePageChange"
            @size-change="handleSizeChange"
          />
        </div>
      </template>
    </SectionCard>

    <el-drawer v-model="detailVisible" title="审计详情" size="480px">
      <dl v-if="activeLog" class="detail-list">
        <dt>时间</dt>
        <dd>{{ formatDateTime(activeLog.created_at) }}</dd>
        <dt>用户</dt>
        <dd>{{ formatUser(activeLog) }}</dd>
        <dt>动作</dt>
        <dd class="text-mono">{{ activeLog.action }}</dd>
        <dt>资源</dt>
        <dd>{{ formatResource(activeLog) }}</dd>
        <dt>IP</dt>
        <dd class="text-mono">{{ activeLog.ip ?? '—' }}</dd>
        <dt>User-Agent</dt>
        <dd class="text-wrap text-muted">{{ activeLog.user_agent ?? '—' }}</dd>
      </dl>

      <div v-if="activeLog" class="detail-block">
        <p class="detail-block__title">变更摘要（已脱敏）</p>
        <pre class="detail-block__json">{{ activeDetailJson }}</pre>
      </div>
    </el-drawer>
  </div>
</template>

<style scoped>
.filter-row__field--narrow {
  min-width: 132px;
}

.filter-row__field--wide {
  min-width: 260px;
  flex: 1 1 260px;
}

.range-hint {
  margin: var(--gov-space-3) var(--gov-space-4) 0;
}

:deep(.el-input-number .el-input__inner) {
  text-align: left;
}

.detail-block {
  margin-top: var(--gov-space-5);
  padding-top: var(--gov-space-3);
  border-top: 1px solid var(--gov-border);
}

.detail-block__title {
  font-size: var(--gov-text-sm);
  font-weight: 600;
  color: var(--gov-text);
  margin-bottom: var(--gov-space-2);
}

.detail-block__json {
  margin: 0;
  padding: var(--gov-space-3);
  max-height: 360px;
  overflow: auto;
  border: 1px solid var(--gov-border);
  border-radius: var(--gov-radius-sm);
  background: var(--gov-surface-muted);
  font-family: var(--gov-font-mono);
  font-size: var(--gov-text-xs);
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
}

.text-wrap {
  white-space: pre-wrap;
  word-break: break-word;
}

.alert-body {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--gov-space-3);
}

.alert-body__detail {
  font-family: var(--gov-font-mono);
  font-size: var(--gov-text-xs);
  color: var(--gov-text-secondary);
}
</style>
