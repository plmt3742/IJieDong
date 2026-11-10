<script setup lang="ts">
import { Document, Refresh, UploadFilled } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { computed, onMounted, ref } from 'vue'

import { getImportErrors, getImportJob, listImports, uploadImport } from '@/api/admin'
import { describeApiError, describeApiErrorDetail } from '@/api/http'
import type { ImportErrorItem, ImportJob, ImportJobDetail } from '@/api/types'
import PageHeader from '@/components/PageHeader.vue'
import SectionCard from '@/components/SectionCard.vue'
import StatusTag from '@/components/StatusTag.vue'
import { formatDateTime, formatInteger, formatNumber } from '@/utils/format'

const MAX_SIZE_MB = 10
const ALLOWED_EXTENSIONS = ['.xls', '.xlsx']

const fileInput = ref<HTMLInputElement | null>(null)
const selectedFile = ref<File | null>(null)
const fileError = ref('')
const dragActive = ref(false)

const mode = ref<'atomic' | 'partial'>('atomic')
const sourceId = ref<number | undefined>(undefined)

const uploading = ref(false)
const progress = ref(0)
const uploadError = ref('')
const uploadErrorDetail = ref('')

const result = ref<ImportJobDetail | null>(null)
const errors = ref<ImportErrorItem[]>([])
const resultLoading = ref(false)

const history = ref<ImportJob[]>([])
const historyTotal = ref(0)
const historyPage = ref(1)
const historyPageSize = ref(10)
const historyLoading = ref(false)
const historyError = ref('')

const canSubmit = computed(() => Boolean(selectedFile.value) && !uploading.value)

function acceptFile(candidate: File): void {
  const lowerName = candidate.name.toLowerCase()
  if (!ALLOWED_EXTENSIONS.some((extension) => lowerName.endsWith(extension))) {
    fileError.value = '仅支持 .xls 或 .xlsx 文件'
    return
  }
  if (candidate.size > MAX_SIZE_MB * 1024 * 1024) {
    fileError.value = `文件大小不能超过 ${MAX_SIZE_MB} MB`
    return
  }
  selectedFile.value = candidate
  fileError.value = ''
  result.value = null
  errors.value = []
  uploadError.value = ''
  uploadErrorDetail.value = ''
}

function handleSelect(event: Event): void {
  const input = event.target as HTMLInputElement
  const candidate = input.files?.[0]
  if (candidate) acceptFile(candidate)
}

function handleDrop(event: DragEvent): void {
  dragActive.value = false
  const candidate = event.dataTransfer?.files?.[0]
  if (candidate) acceptFile(candidate)
}

function openFileDialog(): void {
  fileInput.value?.click()
}

function clearFile(): void {
  selectedFile.value = null
  progress.value = 0
  if (fileInput.value) fileInput.value.value = ''
}

function fileSizeLabel(size: number): string {
  if (size >= 1024 * 1024) return `${formatNumber(size / 1024 / 1024, 1)} MB`
  return `${formatNumber(size / 1024, 0)} KB`
}

async function loadJobErrors(job: ImportJobDetail): Promise<void> {
  if (Array.isArray(job.errors) && job.errors.length > 0) {
    errors.value = job.errors
    return
  }
  if ((job.error_rows ?? 0) <= 0) {
    errors.value = []
    return
  }
  try {
    errors.value = await getImportErrors(job.id)
  } catch {
    errors.value = []
  }
}

async function submitImport(): Promise<void> {
  if (!selectedFile.value) {
    fileError.value = '请先选择要导入的文件'
    return
  }

  uploading.value = true
  progress.value = 0
  uploadError.value = ''
  uploadErrorDetail.value = ''

  const form = new FormData()
  form.append('file', selectedFile.value)
  form.append('mode', mode.value)
  if (typeof sourceId.value === 'number') {
    form.append('source_id', String(sourceId.value))
  }

  try {
    const job = await uploadImport(form, (percent) => {
      progress.value = percent
    })
    result.value = job
    await loadJobErrors(job)
    if (job.status === 'failed') {
      ElMessage.warning('导入失败，请查看错误明细')
    } else if (job.status === 'partial') {
      ElMessage.warning('导入部分成功，请核对错误行')
    } else {
      ElMessage.success('导入完成')
    }
    historyPage.value = 1
    void loadHistory()
  } catch (error) {
    uploadError.value = describeApiError(error)
    uploadErrorDetail.value = describeApiErrorDetail(error)
  } finally {
    uploading.value = false
  }
}

async function loadHistory(): Promise<void> {
  historyLoading.value = true
  historyError.value = ''
  try {
    const page = await listImports({ page: historyPage.value, page_size: historyPageSize.value })
    history.value = page.data
    historyTotal.value = page.meta.total
  } catch (error) {
    history.value = []
    historyTotal.value = 0
    historyError.value = describeApiError(error)
  } finally {
    historyLoading.value = false
  }
}

async function openHistoryJob(job: ImportJob): Promise<void> {
  resultLoading.value = true
  errors.value = []
  uploadError.value = ''
  uploadErrorDetail.value = ''
  try {
    const detail = await getImportJob(job.id)
    result.value = detail
    await loadJobErrors(detail)
  } catch (error) {
    uploadError.value = describeApiError(error)
    uploadErrorDetail.value = describeApiErrorDetail(error)
  } finally {
    resultLoading.value = false
  }
}

function handleHistoryPageChange(next: number): void {
  historyPage.value = next
  void loadHistory()
}

function handleHistorySizeChange(next: number): void {
  historyPageSize.value = next
  historyPage.value = 1
  void loadHistory()
}

const errorColumns = computed(() => {
  const sample = errors.value[0]
  return {
    hasRow: Boolean(sample?.row !== undefined || sample?.row_number !== undefined),
    hasColumn: Boolean(sample?.column || sample?.field),
  }
})

function errorRowIndex(item: ImportErrorItem): string {
  const value = item.row ?? item.row_number
  return typeof value === 'number' ? String(value) : '—'
}

function errorColumn(item: ImportErrorItem): string {
  return item.column ?? item.field ?? '—'
}

onMounted(() => {
  void loadHistory()
})
</script>

<template>
  <div class="page">
    <PageHeader
      title="数据导入"
      description="上传 .xls / .xlsx 文件写入数据值。atomic 模式有错整批不写，partial 模式写入通过行。"
    >
      <template #actions>
        <el-button :icon="Refresh" @click="loadHistory">刷新记录</el-button>
      </template>
    </PageHeader>

    <div class="import-grid">
      <SectionCard title="上传文件" hint="单文件不超过 10 MB，最多 5000 行">
        <div
          class="dropzone"
          :class="{ 'is-active': dragActive, 'is-filled': Boolean(selectedFile) }"
          role="button"
          tabindex="0"
          @click="openFileDialog"
          @keydown.enter="openFileDialog"
          @keydown.space.prevent="openFileDialog"
          @dragover.prevent="dragActive = true"
          @dragleave.prevent="dragActive = false"
          @drop.prevent="handleDrop"
        >
          <input
            ref="fileInput"
            class="dropzone__input"
            type="file"
            accept=".xls,.xlsx"
            @change="handleSelect"
          />
          <el-icon class="dropzone__icon"><UploadFilled /></el-icon>
          <p class="dropzone__title">
            {{ selectedFile ? selectedFile.name : '拖拽文件到此处，或点击选择文件' }}
          </p>
          <p class="dropzone__hint">
            {{
              selectedFile
                ? `${fileSizeLabel(selectedFile.size)} · 已选择，等待导入`
                : '支持 Excel 97-2003 (.xls) 与 Excel 工作簿 (.xlsx)'
            }}
          </p>
        </div>

        <div v-if="selectedFile" class="selected-file">
          <el-icon><Document /></el-icon>
          <span class="selected-file__name">{{ selectedFile.name }}</span>
          <el-button link type="danger" @click.stop="clearFile">移除</el-button>
        </div>

        <el-alert
          v-if="fileError"
          class="inline-alert"
          :title="fileError"
          type="error"
          :closable="false"
          show-icon
        />

        <div class="import-form">
          <div class="import-form__field">
            <span class="filter-row__label">导入模式</span>
            <el-radio-group v-model="mode">
              <el-radio value="atomic">atomic（整批校验）</el-radio>
              <el-radio value="partial">partial（写入通过行）</el-radio>
            </el-radio-group>
            <p class="import-form__hint">
              {{
                mode === 'atomic'
                  ? '任意一行校验失败时整批不写入，适合正式批次。'
                  : '校验通过的行会写入，失败行汇总到错误表，适合补数。'
              }}
            </p>
          </div>

          <div class="import-form__field">
            <span class="filter-row__label">数据来源 ID（可选）</span>
            <el-input-number
              v-model="sourceId"
              :min="1"
              :controls="false"
              placeholder="留空则使用默认演示来源"
              style="width: 220px"
            />
          </div>

          <div class="import-form__actions">
            <el-button type="primary" :disabled="!canSubmit" :loading="uploading" @click="submitImport">
              开始导入
            </el-button>
            <span v-if="uploading" class="text-muted">正在上传并校验，请勿关闭页面</span>
          </div>

          <el-progress v-if="uploading || progress > 0" :percentage="progress" :stroke-width="8" />
        </div>

        <el-alert
          v-if="uploadError"
          class="inline-alert"
          type="error"
          show-icon
          :closable="false"
        >
          <template #title>{{ uploadError }}</template>
          <template #default>
            <span class="text-mono">{{ uploadErrorDetail }}</span>
          </template>
        </el-alert>
      </SectionCard>

      <SectionCard title="导入结果" hint="展示本次或历史批次的统计与错误行">
        <el-skeleton v-if="resultLoading" animated :rows="4" />

        <el-empty v-else-if="!result" description="尚未执行导入" :image-size="72" />

        <template v-else>
          <div class="result-head">
            <div class="cell-stack">
              <span class="result-head__name">{{ result.filename ?? '未命名文件' }}</span>
              <span class="cell-stack__meta">
                批次 {{ result.id }} · 模式 {{ result.mode ?? '—' }} ·
                {{ formatDateTime(result.finished_at ?? result.created_at) }}
              </span>
            </div>
            <StatusTag kind="import" :value="result.status" />
          </div>

          <div class="result-stats">
            <div class="result-stat">
              <span class="result-stat__label">总行数</span>
              <span class="result-stat__value">{{ formatInteger(result.total_rows ?? 0) }}</span>
            </div>
            <div class="result-stat">
              <span class="result-stat__label">成功</span>
              <span class="result-stat__value result-stat__value--success">
                {{ formatInteger(result.success_rows ?? 0) }}
              </span>
            </div>
            <div class="result-stat">
              <span class="result-stat__label">失败</span>
              <span class="result-stat__value result-stat__value--danger">
                {{ formatInteger(result.error_rows ?? 0) }}
              </span>
            </div>
          </div>

          <p v-if="(result.error_rows ?? 0) === 0" class="text-muted result-hint">
            该批次没有错误行。
          </p>

          <el-table
            v-else
            :data="errors"
            border
            size="small"
            max-height="260"
            empty-text="未返回错误明细，可稍后重新查看批次"
          >
            <el-table-column v-if="errorColumns.hasRow" label="行号" width="70">
              <template #default="{ row }">{{ errorRowIndex(row as ImportErrorItem) }}</template>
            </el-table-column>
            <el-table-column v-if="errorColumns.hasColumn" label="列" width="120">
              <template #default="{ row }">{{ errorColumn(row as ImportErrorItem) }}</template>
            </el-table-column>
            <el-table-column label="错误码" width="150">
              <template #default="{ row }">
                <span class="text-mono">{{ (row as ImportErrorItem).code ?? '—' }}</span>
              </template>
            </el-table-column>
            <el-table-column label="说明" min-width="180">
              <template #default="{ row }">{{ (row as ImportErrorItem).message ?? '—' }}</template>
            </el-table-column>
            <el-table-column label="建议" min-width="160">
              <template #default="{ row }">
                {{ (row as ImportErrorItem).suggestion ?? '—' }}
              </template>
            </el-table-column>
          </el-table>
        </template>
      </SectionCard>
    </div>

    <SectionCard title="导入记录" :hint="`来自 GET /admin/imports，共 ${historyTotal} 条`" flush>
      <el-alert
        v-if="historyError"
        class="history-alert"
        :title="historyError"
        type="warning"
        :closable="false"
        show-icon
      />

      <el-table
        v-loading="historyLoading"
        :data="history"
        stripe
        border
        empty-text="还没有导入记录"
        style="width: 100%"
      >
        <el-table-column prop="id" label="批次" width="80" />
        <el-table-column label="文件名" min-width="200">
          <template #default="{ row }">
            <span class="history-file">{{ (row as ImportJob).filename ?? '未命名文件' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="模式" width="92">
          <template #default="{ row }">{{ (row as ImportJob).mode ?? '—' }}</template>
        </el-table-column>
        <el-table-column label="状态" width="110" align="center">
          <template #default="{ row }">
            <StatusTag kind="import" :value="(row as ImportJob).status" />
          </template>
        </el-table-column>
        <el-table-column label="总行数" width="90" align="right">
          <template #default="{ row }">{{ formatInteger((row as ImportJob).total_rows ?? 0) }}</template>
        </el-table-column>
        <el-table-column label="成功" width="90" align="right">
          <template #default="{ row }">{{ formatInteger((row as ImportJob).success_rows ?? 0) }}</template>
        </el-table-column>
        <el-table-column label="失败" width="90" align="right">
          <template #default="{ row }">{{ formatInteger((row as ImportJob).error_rows ?? 0) }}</template>
        </el-table-column>
        <el-table-column label="创建时间" width="152">
          <template #default="{ row }">
            <span class="text-muted">{{ formatDateTime((row as ImportJob).created_at) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="96" fixed="right" align="center">
          <template #default="{ row }">
            <el-button link type="primary" @click="openHistoryJob(row as ImportJob)">查看</el-button>
          </template>
        </el-table-column>
      </el-table>

      <template #footer>
        <div class="pager">
          <el-pagination
            background
            layout="total, sizes, prev, pager, next"
            :current-page="historyPage"
            :page-size="historyPageSize"
            :page-sizes="[10, 20, 50]"
            :total="historyTotal"
            @current-change="handleHistoryPageChange"
            @size-change="handleHistorySizeChange"
          />
        </div>
      </template>
    </SectionCard>
  </div>
</template>

<style scoped>
.import-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: var(--gov-space-4);
}

.dropzone {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--gov-space-2);
  padding: var(--gov-space-8) var(--gov-space-4);
  border: 1px dashed var(--gov-border-strong);
  border-radius: var(--gov-radius-md);
  background: var(--gov-surface-muted);
  cursor: pointer;
  text-align: center;
}

.dropzone:hover,
.dropzone:focus-visible,
.dropzone.is-active {
  border-color: var(--gov-primary);
  background: var(--gov-primary-soft);
  outline: none;
}

.dropzone.is-filled {
  border-style: solid;
}

.dropzone__input {
  display: none;
}

.dropzone__icon {
  font-size: 28px;
  color: var(--gov-primary);
}

.dropzone__title {
  font-size: var(--gov-text-sm);
  color: var(--gov-text);
  word-break: break-all;
}

.dropzone__hint {
  font-size: var(--gov-text-xs);
  color: var(--gov-text-muted);
}

.selected-file {
  display: flex;
  align-items: center;
  gap: var(--gov-space-2);
  margin-top: var(--gov-space-2);
  padding: var(--gov-space-2) var(--gov-space-3);
  border: 1px solid var(--gov-border);
  border-radius: var(--gov-radius-sm);
  background: var(--gov-surface);
  font-size: var(--gov-text-sm);
}

.selected-file__name {
  flex: 1 1 auto;
  word-break: break-all;
}

.import-form {
  display: flex;
  flex-direction: column;
  gap: var(--gov-space-3);
  margin-top: var(--gov-space-4);
  padding-top: var(--gov-space-4);
  border-top: 1px solid var(--gov-border);
}

.import-form__field {
  display: flex;
  flex-direction: column;
  gap: var(--gov-space-1);
}

.import-form__hint {
  font-size: var(--gov-text-xs);
  color: var(--gov-text-muted);
}

.import-form__actions {
  display: flex;
  align-items: center;
  gap: var(--gov-space-3);
}

.inline-alert {
  margin-top: var(--gov-space-3);
}

.result-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--gov-space-3);
}

.result-head__name {
  font-size: var(--gov-text-sm);
  word-break: break-all;
}

.result-stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--gov-space-2);
  margin: var(--gov-space-3) 0;
}

.result-stat {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: var(--gov-space-3);
  border: 1px solid var(--gov-border);
  border-radius: var(--gov-radius-sm);
  background: var(--gov-surface-muted);
}

.result-stat__label {
  font-size: var(--gov-text-xs);
  color: var(--gov-text-muted);
}

.result-stat__value {
  font-size: var(--gov-text-xl);
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.result-stat__value--success {
  color: var(--gov-success);
}

.result-stat__value--danger {
  color: var(--gov-danger);
}

.result-hint {
  font-size: var(--gov-text-xs);
}

.history-alert {
  margin: var(--gov-space-3) var(--gov-space-4) 0;
}

.history-file {
  word-break: break-all;
}

@media (max-width: 1180px) {
  .import-grid {
    grid-template-columns: 1fr;
  }
}
</style>
