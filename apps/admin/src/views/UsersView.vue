<script setup lang="ts">
import { Refresh, Search } from '@element-plus/icons-vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { computed, onMounted, reactive, ref } from 'vue'

import { listUsers, updateUser } from '@/api/admin'
import { ApiError, describeApiError, describeApiErrorDetail } from '@/api/http'
import type { AdminUser, Role } from '@/api/types'
import PageHeader from '@/components/PageHeader.vue'
import SectionCard from '@/components/SectionCard.vue'
import StatusTag from '@/components/StatusTag.vue'
import { useRequest } from '@/composables/useRequest'
import { ROLE_LABELS, formatDateTime } from '@/utils/format'

type AssignableRole = Exclude<Role, 'guest' | 'applicant'>

interface Filters {
  role: string | undefined
  status: string | undefined
  q: string
}

const filters = reactive<Filters>({ role: undefined, status: undefined, q: '' })
const page = ref(1)
const pageSize = ref(20)

const roleOptions: AssignableRole[] = ['viewer', 'editor', 'approver', 'admin']
const statusOptions = [
  { value: 'active', label: '启用' },
  { value: 'disabled', label: '禁用' },
]

const listRequest = useRequest(() =>
  listUsers({
    role: filters.role,
    status: filters.status,
    q: filters.q.trim() || undefined,
    page: page.value,
    page_size: pageSize.value,
  }),
)

const rows = computed<AdminUser[]>(() => listRequest.data.value?.data ?? [])
const total = computed(() => listRequest.data.value?.meta.total ?? 0)

/* ---- Edit dialog ---- */

interface EditForm {
  role: AssignableRole
  status: 'active' | 'disabled'
  unit: string
}

const editVisible = ref(false)
const editTarget = ref<AdminUser | null>(null)
const editFormRef = ref<FormInstance>()
const editForm = reactive<EditForm>({ role: 'viewer', status: 'active', unit: '' })
const editSubmitting = ref(false)
const editError = ref('')
const editErrorDetail = ref('')
const editProtected = ref(false)

const editRules: FormRules<EditForm> = {
  role: [{ required: true, message: '请选择角色', trigger: 'change' }],
  status: [{ required: true, message: '请选择状态', trigger: 'change' }],
  unit: [{ max: 50, message: '单位不超过 50 个字符', trigger: 'blur' }],
}

function openEdit(user: AdminUser): void {
  editTarget.value = user
  editForm.role = (roleOptions.includes(user.role as AssignableRole)
    ? user.role
    : 'viewer') as AssignableRole
  editForm.status = user.status === 'disabled' ? 'disabled' : 'active'
  editForm.unit = user.unit ?? ''
  editError.value = ''
  editErrorDetail.value = ''
  editProtected.value = false
  editVisible.value = true
}

async function submitEdit(): Promise<void> {
  if (!editFormRef.value || !editTarget.value) return
  const valid = await editFormRef.value.validate().catch(() => false)
  if (!valid) return

  editSubmitting.value = true
  editError.value = ''
  editErrorDetail.value = ''
  editProtected.value = false
  try {
    await updateUser(editTarget.value.id, {
      role: editForm.role,
      status: editForm.status,
      unit: editForm.unit.trim() || undefined,
    })
    ElMessage.success('用户信息已更新')
    editVisible.value = false
    void listRequest.run()
  } catch (error) {
    editError.value = describeApiError(error)
    editErrorDetail.value = describeApiErrorDetail(error)
    if (error instanceof ApiError && error.code === 'LAST_ADMIN_PROTECTED') {
      editProtected.value = true
    }
  } finally {
    editSubmitting.value = false
  }
}

/* ---- Query helpers ---- */

function applyFilters(): void {
  page.value = 1
  void listRequest.run()
}

function resetFilters(): void {
  filters.role = undefined
  filters.status = undefined
  filters.q = ''
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
      title="用户管理"
      description="查看用户、调整角色与启停状态。最后一个管理员不能被禁用或降级，所有变更写入审计。"
    >
      <template #actions>
        <el-button :icon="Refresh" @click="listRequest.run()">刷新</el-button>
      </template>
    </PageHeader>

    <SectionCard title="筛选条件" flush>
      <div class="panel__body">
        <div class="filter-row">
          <div class="filter-row__field">
            <span class="filter-row__label">关键词</span>
            <el-input
              v-model="filters.q"
              placeholder="用户名 / 姓名 / 单位"
              clearable
              @keyup.enter="applyFilters"
            />
          </div>
          <div class="filter-row__field filter-row__field--narrow">
            <span class="filter-row__label">角色</span>
            <el-select v-model="filters.role" clearable placeholder="全部角色">
              <el-option
                v-for="role in roleOptions"
                :key="role"
                :label="ROLE_LABELS[role]"
                :value="role"
              />
            </el-select>
          </div>
          <div class="filter-row__field filter-row__field--narrow">
            <span class="filter-row__label">状态</span>
            <el-select v-model="filters.status" clearable placeholder="全部状态">
              <el-option
                v-for="option in statusOptions"
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

    <SectionCard title="用户列表" :hint="`共 ${total} 人`" flush>
      <el-table
        v-loading="listRequest.loading.value"
        :data="rows"
        stripe
        border
        style="width: 100%"
        empty-text="没有符合条件的用户"
      >
        <el-table-column label="用户名" width="140">
          <template #default="{ row }">
            <span class="text-mono">{{ (row as AdminUser).username }}</span>
          </template>
        </el-table-column>
        <el-table-column label="姓名" min-width="120">
          <template #default="{ row }">{{ (row as AdminUser).display_name }}</template>
        </el-table-column>
        <el-table-column label="单位" min-width="160">
          <template #default="{ row }">{{ (row as AdminUser).unit ?? '—' }}</template>
        </el-table-column>
        <el-table-column label="手机号" width="132">
          <template #default="{ row }">
            <span class="text-mono">{{ (row as AdminUser).phone ?? '—' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="角色" width="104" align="center">
          <template #default="{ row }">
            <StatusTag kind="role" :value="(row as AdminUser).role" />
          </template>
        </el-table-column>
        <el-table-column label="状态" width="92" align="center">
          <template #default="{ row }">
            <StatusTag kind="user" :value="(row as AdminUser).status" />
          </template>
        </el-table-column>
        <el-table-column label="最后登录" width="152">
          <template #default="{ row }">
            <span class="text-muted">{{ formatDateTime((row as AdminUser).last_login_at) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="88" fixed="right" align="center">
          <template #default="{ row }">
            <el-button link type="primary" @click="openEdit(row as AdminUser)">编辑</el-button>
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

    <el-dialog v-model="editVisible" title="编辑用户" width="480px" :close-on-click-modal="false">
      <div v-if="editTarget" class="dialog-summary">
        <span>{{ editTarget.display_name }}（{{ editTarget.username }}）</span>
        <span class="text-muted">{{ editTarget.unit ?? '未填写单位' }}</span>
      </div>

      <el-alert
        v-if="editError"
        class="inline-alert"
        :type="editProtected ? 'warning' : 'error'"
        show-icon
        :closable="false"
      >
        <template #title>{{ editError }}</template>
        <template #default>
          <span class="text-mono">{{ editErrorDetail }}</span>
        </template>
      </el-alert>

      <el-form ref="editFormRef" :model="editForm" :rules="editRules" label-position="top">
        <el-form-item label="角色" prop="role">
          <el-select v-model="editForm.role" style="width: 100%">
            <el-option
              v-for="role in roleOptions"
              :key="role"
              :label="ROLE_LABELS[role]"
              :value="role"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="状态" prop="status">
          <el-select v-model="editForm.status" style="width: 100%">
            <el-option
              v-for="option in statusOptions"
              :key="option.value"
              :label="option.label"
              :value="option.value"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="所属单位" prop="unit">
          <el-input v-model="editForm.unit" maxlength="50" show-word-limit />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" :loading="editSubmitting" @click="submitEdit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.filter-row__field--narrow {
  min-width: 132px;
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

.inline-alert {
  margin-bottom: var(--gov-space-3);
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
