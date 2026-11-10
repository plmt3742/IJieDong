<script setup lang="ts">
import { Refresh, Search } from '@element-plus/icons-vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { computed, onMounted, reactive, ref, watch } from 'vue'

import { approveApplication, listApplications, rejectApplication } from '@/api/admin'
import { ApiError, describeApiError, describeApiErrorDetail } from '@/api/http'
import type { ApplicationItem, ApplicationStatus, ApproveResult, Role } from '@/api/types'
import PageHeader from '@/components/PageHeader.vue'
import SectionCard from '@/components/SectionCard.vue'
import StatusTag from '@/components/StatusTag.vue'
import { useRequest } from '@/composables/useRequest'
import { useAuthStore } from '@/stores/auth'
import { ROLE_LABELS, formatDateTime } from '@/utils/format'

type AssignableRole = Exclude<Role, 'guest' | 'applicant'>

const auth = useAuthStore()

const activeStatus = ref<ApplicationStatus>('pending')
const keyword = ref('')
const page = ref(1)
const pageSize = ref(20)

const tabs: Array<{ name: ApplicationStatus; label: string }> = [
  { name: 'pending', label: '待审批' },
  { name: 'approved', label: '已批准' },
  { name: 'rejected', label: '已驳回' },
]

const listRequest = useRequest(() =>
  listApplications({
    status: activeStatus.value,
    q: keyword.value.trim() || undefined,
    page: page.value,
    page_size: pageSize.value,
  }),
)

const rows = computed<ApplicationItem[]>(() => listRequest.data.value?.data ?? [])
const total = computed(() => listRequest.data.value?.meta.total ?? 0)

/* ---- Role options: approver may only assign viewer ---- */

const assignableRoles = computed<AssignableRole[]>(() =>
  auth.role === 'admin' ? ['viewer', 'editor', 'approver', 'admin'] : ['viewer'],
)

function roleLabel(role: AssignableRole): string {
  return ROLE_LABELS[role] ?? role
}

/* ---- Self approval guard ---- */

function isSelfApplication(application: ApplicationItem): boolean {
  const currentUserId = auth.user?.id
  if (!currentUserId || !application.user_id) return false
  return application.user_id === currentUserId
}

/* ---- Approve dialog ---- */

const approveVisible = ref(false)
const approveTarget = ref<ApplicationItem | null>(null)
const approveFormRef = ref<FormInstance>()
const approveForm = reactive<{ role: AssignableRole; unit: string; note: string }>({
  role: 'viewer',
  unit: '',
  note: '',
})
const approveSubmitting = ref(false)
const approveError = ref('')
const approveErrorDetail = ref('')

const approveRules: FormRules<typeof approveForm> = {
  role: [{ required: true, message: '请选择批准后的角色', trigger: 'change' }],
  unit: [
    { required: true, message: '请填写所属单位', trigger: 'blur' },
    { min: 2, max: 50, message: '单位长度为 2 到 50 个字符', trigger: 'blur' },
  ],
}

function openApprove(application: ApplicationItem): void {
  approveTarget.value = application
  approveForm.role = 'viewer'
  approveForm.unit = application.unit ?? ''
  approveForm.note = ''
  approveError.value = ''
  approveErrorDetail.value = ''
  approveVisible.value = true
}

async function submitApprove(): Promise<void> {
  if (!approveFormRef.value || !approveTarget.value) return
  const valid = await approveFormRef.value.validate().catch(() => false)
  if (!valid) return

  approveSubmitting.value = true
  approveError.value = ''
  approveErrorDetail.value = ''
  try {
    const result = await approveApplication(approveTarget.value.id, {
      role: approveForm.role,
      unit: approveForm.unit.trim(),
      note: approveForm.note.trim() || undefined,
    })
    approveVisible.value = false
    approveResult.value = result
    approveResultVisible.value = true
    void refresh()
  } catch (error) {
    approveError.value = describeApiError(error)
    approveErrorDetail.value = describeApiErrorDetail(error)
    if (error instanceof ApiError && error.code === 'APPLICATION_NOT_PENDING') {
      void refresh()
    }
  } finally {
    approveSubmitting.value = false
  }
}

/* ---- One-time credential dialog ---- */

const approveResult = ref<ApproveResult | null>(null)
const approveResultVisible = ref(false)

async function copyCredential(): Promise<void> {
  const result = approveResult.value
  if (!result) return
  const text = `用户名：${result.username}\n初始密码：${result.initial_password}`
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success('账号信息已复制')
  } catch {
    ElMessage.warning('浏览器不允许自动复制，请手动选择文本复制')
  }
}

/* ---- Reject dialog ---- */

const rejectVisible = ref(false)
const rejectTarget = ref<ApplicationItem | null>(null)
const rejectFormRef = ref<FormInstance>()
const rejectForm = reactive<{ reason: string }>({ reason: '' })
const rejectSubmitting = ref(false)
const rejectError = ref('')
const rejectErrorDetail = ref('')

const rejectRules: FormRules<typeof rejectForm> = {
  reason: [
    { required: true, message: '请填写驳回原因', trigger: 'blur' },
    { min: 5, max: 200, message: '驳回原因长度为 5 到 200 个字符', trigger: 'blur' },
  ],
}

function openReject(application: ApplicationItem): void {
  rejectTarget.value = application
  rejectForm.reason = ''
  rejectError.value = ''
  rejectErrorDetail.value = ''
  rejectVisible.value = true
}

async function submitReject(): Promise<void> {
  if (!rejectFormRef.value || !rejectTarget.value) return
  const valid = await rejectFormRef.value.validate().catch(() => false)
  if (!valid) return

  rejectSubmitting.value = true
  rejectError.value = ''
  rejectErrorDetail.value = ''
  try {
    await rejectApplication(rejectTarget.value.id, rejectForm.reason.trim())
    ElMessage.success('申请已驳回')
    rejectVisible.value = false
    void refresh()
  } catch (error) {
    rejectError.value = describeApiError(error)
    rejectErrorDetail.value = describeApiErrorDetail(error)
    if (error instanceof ApiError && error.code === 'APPLICATION_NOT_PENDING') {
      void refresh()
    }
  } finally {
    rejectSubmitting.value = false
  }
}

/* ---- Detail drawer ---- */

const detailVisible = ref(false)
const detailTarget = ref<ApplicationItem | null>(null)

function openDetail(application: ApplicationItem): void {
  detailTarget.value = application
  detailVisible.value = true
}

/* ---- Query helpers ---- */

function refresh(): Promise<void> {
  return listRequest.run()
}

function applyKeyword(): void {
  page.value = 1
  void refresh()
}

function resetKeyword(): void {
  keyword.value = ''
  page.value = 1
  void refresh()
}

function handleTabChange(name: string | number): void {
  activeStatus.value = String(name) as ApplicationStatus
  page.value = 1
  void refresh()
}

function handlePageChange(next: number): void {
  page.value = next
  void refresh()
}

function handleSizeChange(next: number): void {
  pageSize.value = next
  page.value = 1
  void refresh()
}

const listErrorText = computed(() =>
  listRequest.error.value ? describeApiError(listRequest.error.value) : '',
)
const listErrorDetail = computed(() =>
  listRequest.error.value ? describeApiErrorDetail(listRequest.error.value) : '',
)

watch(activeStatus, () => {
  page.value = 1
})

onMounted(() => {
  void refresh()
})
</script>

<template>
  <div class="page">
    <PageHeader
      title="申请审批"
      description="审批小程序提交的账号申请：默认批准为查看者，管理员可分配其他角色，审批者只能分配查看者。"
    >
      <template #actions>
        <el-button :icon="Refresh" @click="refresh">刷新</el-button>
      </template>
    </PageHeader>

    <el-alert v-if="listRequest.error.value" type="error" show-icon :closable="false">
      <template #title>{{ listErrorText }}</template>
      <template #default>
        <div class="alert-body">
          <span class="alert-body__detail">{{ listErrorDetail }}</span>
          <el-button size="small" @click="refresh">重试</el-button>
        </div>
      </template>
    </el-alert>

    <SectionCard title="申请列表" :hint="`共 ${total} 条`" flush>
      <div class="table-toolbar">
        <el-tabs class="status-tabs" :model-value="activeStatus" @tab-change="handleTabChange">
          <el-tab-pane v-for="tab in tabs" :key="tab.name" :label="tab.label" :name="tab.name" />
        </el-tabs>

        <div class="toolbar-search">
          <el-input
            v-model="keyword"
            placeholder="姓名 / 单位 / 申请编号"
            clearable
            style="width: 220px"
            @keyup.enter="applyKeyword"
          />
          <el-button type="primary" :icon="Search" @click="applyKeyword">查询</el-button>
          <el-button @click="resetKeyword">重置</el-button>
        </div>
      </div>

      <el-table
        v-loading="listRequest.loading.value"
        :data="rows"
        stripe
        border
        style="width: 100%"
        :empty-text="
          activeStatus === 'pending' ? '当前没有待审批申请' : '该状态下没有申请记录'
        "
      >
        <el-table-column label="申请编号" width="168">
          <template #default="{ row }">
            <span class="text-mono">{{ (row as ApplicationItem).application_no }}</span>
          </template>
        </el-table-column>
        <el-table-column label="申请人" min-width="150">
          <template #default="{ row }">
            <div class="cell-stack">
              <span>{{ (row as ApplicationItem).display_name }}</span>
              <span class="cell-stack__meta">{{ (row as ApplicationItem).unit }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="手机号" width="132">
          <template #default="{ row }">
            <span class="text-mono">{{ (row as ApplicationItem).phone }}</span>
          </template>
        </el-table-column>
        <el-table-column label="提交时间" width="152">
          <template #default="{ row }">
            <span class="text-muted">
              {{
                formatDateTime(
                  (row as ApplicationItem).submitted_at ?? (row as ApplicationItem).created_at,
                )
              }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="重提" width="72" align="center">
          <template #default="{ row }">
            {{ (row as ApplicationItem).resubmit_count ?? 0 }}
          </template>
        </el-table-column>
        <el-table-column label="状态" width="104" align="center">
          <template #default="{ row }">
            <StatusTag kind="application" :value="(row as ApplicationItem).status" />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="196" fixed="right" align="center">
          <template #default="{ row }">
            <div class="row-actions">
              <el-button link type="primary" @click="openDetail(row as ApplicationItem)">详情</el-button>
              <template v-if="(row as ApplicationItem).status === 'pending'">
                <el-tooltip
                  :disabled="!isSelfApplication(row as ApplicationItem)"
                  content="不能审批本人的申请"
                  placement="top"
                >
                  <span>
                    <el-button
                      link
                      type="primary"
                      :disabled="isSelfApplication(row as ApplicationItem)"
                      @click="openApprove(row as ApplicationItem)"
                    >
                      批准
                    </el-button>
                  </span>
                </el-tooltip>
                <el-tooltip
                  :disabled="!isSelfApplication(row as ApplicationItem)"
                  content="不能审批本人的申请"
                  placement="top"
                >
                  <span>
                    <el-button
                      link
                      type="danger"
                      :disabled="isSelfApplication(row as ApplicationItem)"
                      @click="openReject(row as ApplicationItem)"
                    >
                      驳回
                    </el-button>
                  </span>
                </el-tooltip>
              </template>
            </div>
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
            :page-sizes="[10, 20, 50]"
            :total="total"
            @current-change="handlePageChange"
            @size-change="handleSizeChange"
          />
        </div>
      </template>
    </SectionCard>

    <el-dialog v-model="approveVisible" title="批准申请" width="480px" :close-on-click-modal="false">
      <div v-if="approveTarget" class="dialog-summary">
        <span>{{ approveTarget.display_name }} · {{ approveTarget.unit }}</span>
        <span class="text-mono text-muted">{{ approveTarget.application_no }}</span>
      </div>

      <el-alert
        v-if="approveError"
        class="inline-alert"
        type="error"
        show-icon
        :closable="false"
      >
        <template #title>{{ approveError }}</template>
        <template #default>
          <span class="text-mono">{{ approveErrorDetail }}</span>
        </template>
      </el-alert>

      <el-form
        ref="approveFormRef"
        :model="approveForm"
        :rules="approveRules"
        label-position="top"
      >
        <el-form-item label="批准角色" prop="role">
          <el-select v-model="approveForm.role" style="width: 100%">
            <el-option
              v-for="option in assignableRoles"
              :key="option"
              :label="roleLabel(option)"
              :value="option"
            />
          </el-select>
          <p v-if="auth.role !== 'admin'" class="form-hint">审批者只能批准为查看者。</p>
        </el-form-item>

        <el-form-item label="所属单位" prop="unit">
          <el-input v-model="approveForm.unit" maxlength="50" show-word-limit />
        </el-form-item>

        <el-form-item label="审批备注（可选）">
          <el-input
            v-model="approveForm.note"
            type="textarea"
            :rows="2"
            maxlength="200"
            show-word-limit
            placeholder="例如：单位核对通过"
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="approveVisible = false">取消</el-button>
        <el-button type="primary" :loading="approveSubmitting" @click="submitApprove">
          确认批准
        </el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="rejectVisible" title="驳回申请" width="480px" :close-on-click-modal="false">
      <div v-if="rejectTarget" class="dialog-summary">
        <span>{{ rejectTarget.display_name }} · {{ rejectTarget.unit }}</span>
        <span class="text-mono text-muted">{{ rejectTarget.application_no }}</span>
      </div>

      <el-alert
        v-if="rejectError"
        class="inline-alert"
        type="error"
        show-icon
        :closable="false"
      >
        <template #title>{{ rejectError }}</template>
        <template #default>
          <span class="text-mono">{{ rejectErrorDetail }}</span>
        </template>
      </el-alert>

      <el-form ref="rejectFormRef" :model="rejectForm" :rules="rejectRules" label-position="top">
        <el-form-item label="驳回原因" prop="reason">
          <el-input
            v-model="rejectForm.reason"
            type="textarea"
            :rows="4"
            maxlength="200"
            show-word-limit
            placeholder="请说明驳回原因，申请者可在小程序查看"
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="rejectVisible = false">取消</el-button>
        <el-button type="danger" :loading="rejectSubmitting" @click="submitReject">
          确认驳回
        </el-button>
      </template>
    </el-dialog>

    <el-drawer v-model="detailVisible" title="申请详情" size="440px">
      <dl v-if="detailTarget" class="detail-list">
        <dt>申请编号</dt>
        <dd class="text-mono">{{ detailTarget.application_no }}</dd>
        <dt>姓名</dt>
        <dd>{{ detailTarget.display_name }}</dd>
        <dt>单位</dt>
        <dd>{{ detailTarget.unit }}</dd>
        <dt>手机号</dt>
        <dd class="text-mono">{{ detailTarget.phone ?? '—' }}</dd>
        <dt>状态</dt>
        <dd><StatusTag kind="application" :value="detailTarget.status" /></dd>
        <dt>提交时间</dt>
        <dd>{{ formatDateTime(detailTarget.submitted_at ?? detailTarget.created_at) }}</dd>
        <dt>重提次数</dt>
        <dd>{{ detailTarget.resubmit_count ?? 0 }}</dd>
        <dt v-if="detailTarget.reason">申请说明</dt>
        <dd v-if="detailTarget.reason" class="text-wrap">{{ detailTarget.reason }}</dd>
        <dt v-if="detailTarget.reject_reason">驳回原因</dt>
        <dd v-if="detailTarget.reject_reason" class="text-wrap">
          {{ detailTarget.reject_reason }}
        </dd>
        <dt v-if="detailTarget.reviewed_at">审批时间</dt>
        <dd v-if="detailTarget.reviewed_at">{{ formatDateTime(detailTarget.reviewed_at) }}</dd>
      </dl>
    </el-drawer>

    <el-dialog
      v-model="approveResultVisible"
      title="账号已创建"
      width="480px"
      :close-on-click-modal="false"
    >
      <el-alert
        type="warning"
        show-icon
        :closable="false"
        title="初始密码只显示一次"
        description="请通过安全渠道转交申请人。关闭后无法再次查看，只能由管理员重置密码。"
      />

      <dl v-if="approveResult" class="detail-list credential">
        <dt>用户名</dt>
        <dd class="text-mono">{{ approveResult.username }}</dd>
        <dt>角色</dt>
        <dd>{{ ROLE_LABELS[approveResult.role] ?? approveResult.role }}</dd>
        <dt>初始密码</dt>
        <dd class="text-mono credential__password">{{ approveResult.initial_password }}</dd>
      </dl>

      <template #footer>
        <el-button @click="copyCredential">复制账号信息</el-button>
        <el-button type="primary" @click="approveResultVisible = false">我已记录</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.status-tabs {
  flex: 1 1 auto;
  min-width: 260px;
}

.status-tabs :deep(.el-tabs__header) {
  margin-bottom: 0;
}

.toolbar-search {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--gov-space-2);
}

.table-toolbar {
  align-items: center;
}

.row-actions {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--gov-space-2);
}

.dialog-summary {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--gov-space-2);
  margin-bottom: var(--gov-space-3);
  padding-bottom: var(--gov-space-2);
  border-bottom: 1px solid var(--gov-border);
  font-size: var(--gov-text-sm);
}

.form-hint {
  margin: var(--gov-space-1) 0 0;
  font-size: var(--gov-text-xs);
  color: var(--gov-text-muted);
}

.inline-alert {
  margin-bottom: var(--gov-space-3);
}

.credential {
  margin-top: var(--gov-space-4);
  padding-top: var(--gov-space-3);
  border-top: 1px solid var(--gov-border);
}

.credential__password {
  font-size: var(--gov-text-base);
  font-weight: 600;
  letter-spacing: 0.04em;
  user-select: all;
  word-break: break-all;
}

.text-wrap {
  white-space: pre-wrap;
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
