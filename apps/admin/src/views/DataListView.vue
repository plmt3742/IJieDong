<script setup lang="ts">
import { Refresh, Search } from '@element-plus/icons-vue'
import { computed, onMounted, reactive, ref } from 'vue'

import { listDataValues } from '@/api/dataValues'
import { getIndicator, listIndicators } from '@/api/indicators'
import { describeApiError, describeApiErrorDetail } from '@/api/http'
import { listRegions } from '@/api/regions'
import type { DataValue, Indicator, Region } from '@/api/types'
import PageHeader from '@/components/PageHeader.vue'
import SectionCard from '@/components/SectionCard.vue'
import StatusTag from '@/components/StatusTag.vue'
import { useRequest } from '@/composables/useRequest'
import {
  LEVEL_LABELS,
  QUALITY_LABELS,
  REGION_CATEGORY_LABELS,
  formatDateTime,
  formatNumber,
  truncateText,
  VALUE_TYPE_LABELS,
} from '@/utils/format'

interface Filters {
  region_code: string | undefined
  indicator_code: string | undefined
  period_year: number
  quality_status: string | undefined
}

const filters = reactive<Filters>({
  region_code: undefined,
  indicator_code: undefined,
  period_year: 2025,
  quality_status: undefined,
})

const page = ref(1)
const pageSize = ref(20)

const yearOptions = [2024, 2025, 2026]
const qualityOptions = Object.entries(QUALITY_LABELS).map(([value, label]) => ({ value, label }))

const regionOptions = ref<Region[]>([])
const regionLoading = ref(false)
const indicatorOptions = ref<Indicator[]>([])
const indicatorLoading = ref(false)

const listRequest = useRequest(() =>
  listDataValues({
    region_code: filters.region_code,
    indicator_code: filters.indicator_code,
    period_year: filters.period_year,
    quality_status: filters.quality_status,
    page: page.value,
    page_size: pageSize.value,
  }),
)

const rows = computed<DataValue[]>(() => listRequest.data.value?.data ?? [])
const total = computed(() => listRequest.data.value?.meta.total ?? 0)

const indicatorMap = computed(() => {
  const map = new Map<number, Indicator>()
  for (const indicator of indicatorOptions.value) map.set(indicator.id, indicator)
  return map
})

async function searchRegions(keyword: string): Promise<void> {
  regionLoading.value = true
  try {
    const result = await listRegions({
      q: keyword.trim() || undefined,
      page_size: 20,
      enabled: true,
    })
    regionOptions.value = result.data
  } catch {
    regionOptions.value = []
  } finally {
    regionLoading.value = false
  }
}

async function loadIndicators(): Promise<void> {
  indicatorLoading.value = true
  try {
    indicatorOptions.value = await listIndicators()
  } catch {
    indicatorOptions.value = []
  } finally {
    indicatorLoading.value = false
  }
}

function regionLabel(region: Region): string {
  return `${region.name} · ${LEVEL_LABELS[region.level] ?? region.level}`
}

function precisionOf(row: DataValue): number {
  const indicator = indicatorMap.value.get(row.indicator_id)
  if (!indicator) return 2
  if (indicator.value_type === 'integer') return 0
  return indicator.precision ?? 2
}

function displayValue(row: DataValue): string {
  if (row.value_text) return truncateText(row.value_text, 40)
  if (row.value_number === null) {
    return QUALITY_LABELS[row.quality_status] ?? '暂无数据'
  }
  return formatNumber(row.value_number, precisionOf(row))
}

function applyFilters(): void {
  page.value = 1
  void listRequest.run()
}

function resetFilters(): void {
  filters.region_code = undefined
  filters.indicator_code = undefined
  filters.period_year = 2025
  filters.quality_status = undefined
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
const activeRow = ref<DataValue | null>(null)

function openDetail(row: DataValue): void {
  activeRow.value = row
  detailVisible.value = true
}

/* ---- Indicator drawer ---- */

const indicatorVisible = ref(false)
const indicatorLoadingDetail = ref(false)
const indicatorDetail = ref<Indicator | null>(null)
const indicatorError = ref('')

async function openIndicator(row: DataValue): Promise<void> {
  indicatorVisible.value = true
  indicatorDetail.value = null
  indicatorError.value = ''
  indicatorLoadingDetail.value = true
  try {
    indicatorDetail.value = await getIndicator(row.indicator_id)
  } catch (error) {
    indicatorError.value = describeApiError(error)
  } finally {
    indicatorLoadingDetail.value = false
  }
}

const activeRowPrecision = computed(() => (activeRow.value ? precisionOf(activeRow.value) : 2))

const listErrorText = computed(() =>
  listRequest.error.value ? describeApiError(listRequest.error.value) : '',
)
const listErrorDetail = computed(() =>
  listRequest.error.value ? describeApiErrorDetail(listRequest.error.value) : '',
)

onMounted(() => {
  void searchRegions('')
  void loadIndicators()
  void listRequest.run()
})
</script>

<template>
  <div class="page">
    <PageHeader
      title="数据列表"
      description="按区域、指标、年份与质量状态查看已发布数据值；空值保留“暂无数据/不适用”，不补 0。"
    >
      <template #actions>
        <el-button :icon="Refresh" @click="listRequest.run()">刷新</el-button>
      </template>
    </PageHeader>

    <SectionCard title="筛选条件" flush>
      <div class="panel__body">
        <div class="filter-row">
          <div class="filter-row__field">
            <span class="filter-row__label">区域</span>
            <el-select
              v-model="filters.region_code"
              filterable
              remote
              clearable
              :remote-method="searchRegions"
              :loading="regionLoading"
              placeholder="全部区域"
            >
              <el-option
                v-for="region in regionOptions"
                :key="region.id"
                :label="regionLabel(region)"
                :value="region.code"
              />
            </el-select>
          </div>

          <div class="filter-row__field">
            <span class="filter-row__label">指标</span>
            <el-select
              v-model="filters.indicator_code"
              filterable
              clearable
              :loading="indicatorLoading"
              placeholder="全部指标"
            >
              <el-option
                v-for="indicator in indicatorOptions"
                :key="indicator.id"
                :label="indicator.name"
                :value="indicator.code"
              />
            </el-select>
          </div>

          <div class="filter-row__field filter-row__field--narrow">
            <span class="filter-row__label">年份</span>
            <el-select v-model="filters.period_year">
              <el-option v-for="year in yearOptions" :key="year" :label="`${year} 年`" :value="year" />
            </el-select>
          </div>

          <div class="filter-row__field">
            <span class="filter-row__label">质量状态</span>
            <el-select v-model="filters.quality_status" clearable placeholder="全部状态">
              <el-option
                v-for="option in qualityOptions"
                :key="option.value"
                :label="option.label"
                :value="option.value"
              />
            </el-select>
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

    <SectionCard title="数据值" :hint="`共 ${total} 条，仅显示已发布数据`" flush>
      <el-table
        v-loading="listRequest.loading.value"
        :data="rows"
        stripe
        border
        size="default"
        empty-text="没有符合条件的数据"
        style="width: 100%"
      >
        <el-table-column label="区域" min-width="180">
          <template #default="{ row }">
            <div class="cell-stack">
              <span>{{ (row as DataValue).region_name }}</span>
              <span class="cell-stack__meta">
                {{ (row as DataValue).region_code }} ·
                {{ LEVEL_LABELS[(row as DataValue).region_level] ?? (row as DataValue).region_level }}
              </span>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="指标" min-width="170">
          <template #default="{ row }">
            <div class="cell-stack">
              <el-button link type="primary" @click="openIndicator(row as DataValue)">
                {{ (row as DataValue).indicator_name }}
              </el-button>
              <span class="cell-stack__meta">{{ (row as DataValue).indicator_code }}</span>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="年份" width="88" align="center">
          <template #default="{ row }">{{ (row as DataValue).period_year }}</template>
        </el-table-column>

        <el-table-column label="数值" min-width="150" align="right">
          <template #default="{ row }">
            <div class="cell-stack cell-stack--end">
              <span class="value-cell">{{ displayValue(row as DataValue) }}</span>
              <span v-if="(row as DataValue).value_number !== null" class="cell-stack__meta">
                {{ (row as DataValue).unit }}
              </span>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="质量状态" width="112" align="center">
          <template #default="{ row }">
            <StatusTag kind="quality" :value="(row as DataValue).quality_status" />
          </template>
        </el-table-column>

        <el-table-column label="发布状态" width="112" align="center">
          <template #default="{ row }">
            <StatusTag kind="publish" :value="(row as DataValue).status" />
          </template>
        </el-table-column>

        <el-table-column label="更新时间" width="152">
          <template #default="{ row }">
            <span class="text-muted">{{ formatDateTime((row as DataValue).updated_at) }}</span>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="88" fixed="right" align="center">
          <template #default="{ row }">
            <el-button link type="primary" @click="openDetail(row as DataValue)">详情</el-button>
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

    <el-drawer v-model="detailVisible" title="数据值详情" size="440px">
      <template v-if="activeRow">
        <dl class="detail-list">
          <dt>区域</dt>
          <dd>{{ activeRow.region_name }}（{{ activeRow.region_code }}）</dd>
          <dt>区域层级</dt>
          <dd>
            {{ LEVEL_LABELS[activeRow.region_level] ?? activeRow.region_level }} ·
            {{ REGION_CATEGORY_LABELS[activeRow.region_category] ?? activeRow.region_category }}
          </dd>
          <dt>指标</dt>
          <dd>{{ activeRow.indicator_name }}（{{ activeRow.indicator_code }}）</dd>
          <dt>年份</dt>
          <dd>{{ activeRow.period_year }} 年</dd>
          <dt>数值</dt>
          <dd>
            {{
              activeRow.value_number === null
                ? QUALITY_LABELS[activeRow.quality_status] ?? '暂无数据'
                : `${formatNumber(activeRow.value_number, activeRowPrecision)} ${activeRow.unit}`
            }}
          </dd>
          <dt>文本值</dt>
          <dd v-if="activeRow.value_text" class="text-wrap">{{ activeRow.value_text }}</dd>
          <dd v-else class="text-muted">无</dd>
          <dt>质量状态</dt>
          <dd><StatusTag kind="quality" :value="activeRow.quality_status" /></dd>
          <dt>发布状态</dt>
          <dd><StatusTag kind="publish" :value="activeRow.status" /></dd>
          <dt>记录 ID</dt>
          <dd class="text-mono">{{ activeRow.id }}</dd>
          <dt>更新时间</dt>
          <dd>{{ formatDateTime(activeRow.updated_at) }}</dd>
        </dl>
        <div class="drawer-actions">
          <el-button type="primary" plain @click="openIndicator(activeRow)">查看指标元数据</el-button>
        </div>
      </template>
    </el-drawer>

    <el-drawer v-model="indicatorVisible" title="指标元数据" size="440px">
      <el-skeleton v-if="indicatorLoadingDetail" animated :rows="6" />
      <el-alert v-else-if="indicatorError" :title="indicatorError" type="error" :closable="false" />
      <dl v-else-if="indicatorDetail" class="detail-list">
        <dt>名称</dt>
        <dd>{{ indicatorDetail.name }}</dd>
        <dt>编码</dt>
        <dd class="text-mono">{{ indicatorDetail.code }}</dd>
        <dt>单位</dt>
        <dd>{{ indicatorDetail.unit }}</dd>
        <dt>值类型</dt>
        <dd>{{ VALUE_TYPE_LABELS[indicatorDetail.value_type] ?? indicatorDetail.value_type }}</dd>
        <dt>分类</dt>
        <dd>{{ indicatorDetail.category ?? '未分类' }}</dd>
        <dt>适用层级</dt>
        <dd>
          {{
            indicatorDetail.applicable_levels
              .map((level) => LEVEL_LABELS[level] ?? level)
              .join(' / ')
          }}
        </dd>
        <dt>展示精度</dt>
        <dd>{{ indicatorDetail.precision }} 位小数</dd>
        <dt>口径说明</dt>
        <dd class="text-wrap">{{ indicatorDetail.description ?? '未填写' }}</dd>
      </dl>
    </el-drawer>
  </div>
</template>

<style scoped>
.filter-row__field--narrow {
  min-width: 110px;
}

.cell-stack--end {
  align-items: flex-end;
  text-align: right;
}

.value-cell {
  font-variant-numeric: tabular-nums;
}

.text-wrap {
  white-space: pre-wrap;
}

.drawer-actions {
  margin-top: var(--gov-space-4);
  padding-top: var(--gov-space-3);
  border-top: 1px solid var(--gov-border);
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
