<script setup lang="ts">
import { Refresh } from '@element-plus/icons-vue'
import type { EChartsOption } from 'echarts'
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

import { listApplications, listImports } from '@/api/admin'
import { getDashboardOverview } from '@/api/dashboard'
import { describeApiError, describeApiErrorDetail, toApiError } from '@/api/http'
import type { DashboardMetric, ImportJob } from '@/api/types'
import MetricBarChart from '@/components/MetricBarChart.vue'
import MetricCard from '@/components/MetricCard.vue'
import PageHeader from '@/components/PageHeader.vue'
import SectionCard from '@/components/SectionCard.vue'
import StatusTag from '@/components/StatusTag.vue'
import { useRequest } from '@/composables/useRequest'
import { useAuthStore } from '@/stores/auth'
import { formatDateTime, formatInteger, formatNumber } from '@/utils/format'

const router = useRouter()
const auth = useAuthStore()

const canViewImports = computed(() => auth.hasRole(['editor', 'admin']))
const canReviewApplications = computed(() => auth.hasRole(['admin', 'approver']))

const periodYear = ref(2025)
const yearOptions = [2024, 2025, 2026]

const overviewRequest = useRequest(() => getDashboardOverview(periodYear.value))

const CORE_ORDER = [
  'area',
  'population_resident',
  'population_household',
  'gdp',
  'budget_revenue',
  'admin_village_count',
]

const metrics = computed<DashboardMetric[]>(() => {
  const list = overviewRequest.data.value?.metrics ?? []
  const ordered = CORE_ORDER.map((code) => list.find((item) => item.code === code)).filter(
    (item): item is DashboardMetric => Boolean(item),
  )
  const extra = list.filter((item) => !CORE_ORDER.includes(item.code))
  return [...ordered, ...extra]
})

const coverage = computed(() => overviewRequest.data.value?.coverage ?? null)
const townCount = computed(() => overviewRequest.data.value?.town_count ?? null)
const dataAsOf = computed(() => overviewRequest.data.value?.data_as_of ?? null)
const periodLabel = computed(() => overviewRequest.data.value?.period_year ?? periodYear.value)

const chartRows = computed(() =>
  metrics.value
    .filter((metric) => metric.value_number !== null)
    .map((metric) => ({
      code: metric.code,
      label: metric.label,
      value: metric.value_number as number,
      unit: metric.unit,
    })),
)

const compactFormatter = (value: number): string =>
  new Intl.NumberFormat('zh-CN', { notation: 'compact', maximumFractionDigits: 1 }).format(value)

const chartOption = computed<EChartsOption>(() => ({
  grid: { left: 12, right: 24, top: 24, bottom: 8, containLabel: true },
  tooltip: {
    trigger: 'axis',
    axisPointer: { type: 'shadow' },
    formatter: (params: unknown) => {
      const list = Array.isArray(params) ? params : [params]
      const first = list[0] as { dataIndex?: number } | undefined
      const index = typeof first?.dataIndex === 'number' ? first.dataIndex : -1
      const row = chartRows.value[index]
      if (!row) return ''
      return `${row.label}<br/>${formatNumber(row.value)} ${row.unit}`
    },
  },
  xAxis: {
    type: 'category',
    data: chartRows.value.map((row) => row.label),
    axisLabel: { interval: 0, width: 76, overflow: 'break', color: '#55636f' },
    axisLine: { lineStyle: { color: '#dfe5eb' } },
    axisTick: { show: false },
  },
  yAxis: {
    type: 'log',
    min: 1,
    axisLabel: { formatter: compactFormatter, color: '#7d8a97' },
    splitLine: { lineStyle: { color: '#eef2f6' } },
  },
  series: [
    {
      name: '指标数值',
      type: 'bar',
      barMaxWidth: 32,
      data: chartRows.value.map((row) => row.value),
      itemStyle: { color: '#1b4f8a', borderRadius: [3, 3, 0, 0] },
    },
  ],
}))

type PanelState = 'loading' | 'ready' | 'empty' | 'unavailable' | 'restricted'

const importsState = ref<PanelState>('loading')
const imports = ref<ImportJob[]>([])
const importsError = ref('')

const pendingState = ref<PanelState>('loading')
const pendingTotal = ref(0)
const pendingError = ref('')

function panelErrorText(error: unknown): string {
  const apiError = toApiError(error)
  if (apiError.status === 403) return '当前角色无权查看该数据'
  if (apiError.status === 404) return '该接口尚未在 Demo v0 后端实现（404）'
  if (apiError.status === 401) return '登录已失效'
  if (apiError.status === 0) return '无法连接后端服务，请确认 API 已启动'
  return describeApiError(error)
}

async function loadImportsPanel(): Promise<void> {
  importsError.value = ''
  if (!canViewImports.value) {
    imports.value = []
    importsState.value = 'restricted'
    return
  }
  importsState.value = 'loading'
  try {
    const page = await listImports({ page: 1, page_size: 5 })
    imports.value = page.data
    importsState.value = page.data.length > 0 ? 'ready' : 'empty'
  } catch (error) {
    importsState.value = 'unavailable'
    importsError.value = panelErrorText(error)
  }
}

async function loadPendingPanel(): Promise<void> {
  pendingError.value = ''
  if (!canReviewApplications.value) {
    pendingTotal.value = 0
    pendingState.value = 'restricted'
    return
  }
  pendingState.value = 'loading'
  try {
    const page = await listApplications({ status: 'pending', page: 1, page_size: 1 })
    pendingTotal.value = page.meta.total
    pendingState.value = 'ready'
  } catch (error) {
    pendingState.value = 'unavailable'
    pendingError.value = panelErrorText(error)
  }
}

function refreshAll(): void {
  void overviewRequest.run()
  void loadImportsPanel()
  void loadPendingPanel()
}

onMounted(() => {
  refreshAll()
})

watch(periodYear, () => {
  void overviewRequest.run()
})

const overviewErrorText = computed(() =>
  overviewRequest.error.value ? describeApiError(overviewRequest.error.value) : '',
)
const overviewErrorDetail = computed(() =>
  overviewRequest.error.value ? describeApiErrorDetail(overviewRequest.error.value) : '',
)
</script>

<template>
  <div class="page">
    <PageHeader
      title="总览"
      description="区级核心指标、数据覆盖、待审申请与最近导入。数值为合成演示数据，空值不补 0。"
    >
      <template #actions>
        <el-select v-model="periodYear" size="default" style="width: 120px">
          <el-option v-for="year in yearOptions" :key="year" :label="`${year} 年`" :value="year" />
        </el-select>
        <el-button :icon="Refresh" @click="refreshAll">刷新</el-button>
      </template>
    </PageHeader>

    <el-alert
      v-if="overviewRequest.error.value"
      :title="overviewErrorText"
      type="error"
      show-icon
      :closable="false"
    >
      <template #default>
        <div class="alert-body">
          <span class="alert-body__detail">{{ overviewErrorDetail }}</span>
          <el-button size="small" @click="overviewRequest.run()">重试</el-button>
        </div>
      </template>
    </el-alert>

    <section v-if="overviewRequest.loading.value && !overviewRequest.data.value" class="metric-grid">
      <div v-for="index in 6" :key="index" class="panel metric-skeleton">
        <el-skeleton animated :rows="2" />
      </div>
    </section>

    <section v-else-if="metrics.length > 0" class="metric-grid">
      <MetricCard
        v-for="metric in metrics"
        :key="metric.code"
        :label="metric.label"
        :value="metric.value_number"
        :unit="metric.unit"
      />
    </section>

    <el-empty v-else-if="!overviewRequest.loading.value" description="暂无核心指标数据" :image-size="88" />

    <div class="overview-split">
      <SectionCard
        title="核心指标数值对比"
        hint="不同指标单位不同，纵轴为对数刻度；具体数值与单位见提示框。"
      >
        <MetricBarChart v-if="chartRows.length > 0" :option="chartOption" :height="300" />
        <el-empty v-else description="没有可绘制的数值指标" :image-size="72" />
      </SectionCard>

      <SectionCard title="数据覆盖" :hint="`统计年度 ${periodLabel}`">
        <div class="coverage">
          <div class="coverage__ring">
            <el-progress
              v-if="coverage !== null"
              type="dashboard"
              :percentage="coverage"
              :width="132"
              :stroke-width="10"
              color="#1b4f8a"
            />
            <div v-else class="coverage__empty">暂无数据</div>
          </div>
          <dl class="detail-list">
            <dt>覆盖率</dt>
            <dd>{{ coverage === null ? '暂无数据' : `${formatNumber(coverage, 1)}%` }}</dd>
            <dt>镇街数量</dt>
            <dd>{{ townCount === null ? '暂无数据' : `${formatInteger(townCount)} 个` }}</dd>
            <dt>数据时点</dt>
            <dd>{{ dataAsOf ? formatDateTime(dataAsOf) : '演示种子数据' }}</dd>
          </dl>
        </div>
      </SectionCard>
    </div>

    <div class="overview-split overview-split--lower">
      <SectionCard title="最近导入" hint="来自 GET /admin/imports，最多 5 条">
        <template #extra>
          <el-button
            v-if="importsState === 'ready' || importsState === 'empty'"
            text
            type="primary"
            @click="router.push('/import')"
          >
            进入导入
          </el-button>
        </template>

        <div v-if="importsState === 'loading'" class="panel-loading">
          <el-skeleton animated :rows="4" />
        </div>

        <el-empty
          v-else-if="importsState === 'restricted'"
          description="当前角色无权查看导入记录"
          :image-size="56"
        />

        <el-alert
          v-else-if="importsState === 'unavailable'"
          :title="importsError"
          type="warning"
          :closable="false"
          show-icon
        >
          <template #default>
            <el-button size="small" @click="loadImportsPanel">重试</el-button>
          </template>
        </el-alert>

        <el-empty
          v-else-if="importsState === 'empty'"
          description="还没有导入记录"
          :image-size="64"
        />

        <ul v-else class="import-list">
          <li v-for="job in imports" :key="job.id" class="import-list__item">
            <div class="cell-stack">
              <span class="import-list__name">{{ job.filename ?? '未命名文件' }}</span>
              <span class="cell-stack__meta">{{ formatDateTime(job.created_at) }}</span>
            </div>
            <div class="import-list__meta">
              <el-tag v-if="job.mode" size="small" effect="plain">{{ job.mode }}</el-tag>
              <span class="import-list__rows">
                {{ formatInteger(job.success_rows ?? 0) }} / {{ formatInteger(job.total_rows ?? 0) }} 行
              </span>
              <StatusTag kind="import" :value="job.status" />
            </div>
          </li>
        </ul>
      </SectionCard>

      <SectionCard title="待审申请" hint="来自 GET /admin/applications?status=pending">
        <div v-if="pendingState === 'loading'" class="panel-loading">
          <el-skeleton animated :rows="3" />
        </div>

        <el-empty
          v-else-if="pendingState === 'restricted'"
          description="当前角色无权查看待审申请"
          :image-size="56"
        />

        <el-alert
          v-else-if="pendingState === 'unavailable'"
          :title="pendingError"
          type="warning"
          :closable="false"
          show-icon
        >
          <template #default>
            <el-button size="small" @click="loadPendingPanel">重试</el-button>
          </template>
        </el-alert>

        <div v-else class="pending">
          <p class="pending__value">{{ formatInteger(pendingTotal) }}</p>
          <p class="pending__label">条待审批申请</p>
          <el-button
            class="pending__action"
            type="primary"
            plain
            @click="router.push('/applications')"
          >
            前往审批
          </el-button>
        </div>
      </SectionCard>
    </div>
  </div>
</template>

<style scoped>
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

.metric-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(184px, 1fr));
  gap: var(--gov-space-3);
}

.metric-skeleton {
  padding: var(--gov-space-4);
  min-height: 108px;
}

.overview-split {
  display: grid;
  grid-template-columns: minmax(0, 2fr) minmax(280px, 1fr);
  gap: var(--gov-space-4);
  align-items: stretch;
}

.overview-split--lower {
  grid-template-columns: minmax(0, 3fr) minmax(260px, 2fr);
}

.coverage {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--gov-space-4);
}

.coverage__ring {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 132px;
  min-height: 132px;
}

.coverage__empty {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 132px;
  height: 132px;
  border: 1px dashed var(--gov-border-strong);
  border-radius: 50%;
  color: var(--gov-text-muted);
  font-size: var(--gov-text-sm);
}

.import-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
}

.import-list__item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--gov-space-3);
  padding: var(--gov-space-2) 0;
  border-bottom: 1px solid var(--gov-border);
}

.import-list__item:last-child {
  border-bottom: none;
}

.import-list__name {
  font-size: var(--gov-text-sm);
  color: var(--gov-text);
  word-break: break-all;
}

.import-list__meta {
  display: flex;
  align-items: center;
  gap: var(--gov-space-2);
  flex: 0 0 auto;
}

.import-list__rows {
  font-size: var(--gov-text-xs);
  color: var(--gov-text-muted);
  font-variant-numeric: tabular-nums;
}

.panel-loading {
  padding: var(--gov-space-2) 0;
}

.pending {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: var(--gov-space-1);
}

.pending__value {
  font-size: 34px;
  font-weight: 600;
  line-height: 1.1;
  color: var(--gov-text);
  font-variant-numeric: tabular-nums;
}

.pending__label {
  font-size: var(--gov-text-sm);
  color: var(--gov-text-secondary);
}

.pending__action {
  margin-top: var(--gov-space-2);
}

@media (max-width: 1180px) {
  .overview-split,
  .overview-split--lower {
    grid-template-columns: 1fr;
  }
}
</style>
