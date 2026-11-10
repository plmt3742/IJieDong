import { cleanParams, getItem, getPage, patchItem, postItem } from './http'
import type {
  AdminUser,
  ApplicationItem,
  ApplicationStatus,
  ApproveApplicationPayload,
  ApproveResult,
  AuditLog,
  AuditLogQuery,
  ImportErrorItem,
  ImportJob,
  ImportJobDetail,
  ListParams,
  PageEnvelope,
  UserPatchPayload,
} from './types'

/* ---- Imports (AD05 / AD06) ---- */

export interface ImportListParams extends ListParams {
  status?: string
}

/** GET /admin/imports */
export async function listImports(params: ImportListParams = {}): Promise<PageEnvelope<ImportJob>> {
  return getPage<ImportJob>('/admin/imports', { params: cleanParams({ ...params }) })
}

/** POST /admin/imports (multipart/form-data) */
export async function uploadImport(
  form: FormData,
  onProgress?: (percent: number) => void,
): Promise<ImportJobDetail> {
  const envelope = await postItem<ImportJobDetail>('/admin/imports', form, {
    timeout: 120000,
    onUploadProgress: (event) => {
      if (!onProgress) return
      const total = event.total ?? 0
      if (total > 0) {
        onProgress(Math.min(100, Math.round((event.loaded / total) * 100)))
      }
    },
  })
  return envelope.data
}

/** GET /admin/imports/{id} */
export async function getImportJob(jobId: number): Promise<ImportJobDetail> {
  const envelope = await getItem<ImportJobDetail>(`/admin/imports/${jobId}`)
  return envelope.data
}

/** GET /admin/imports/{id}/errors */
export async function getImportErrors(jobId: number): Promise<ImportErrorItem[]> {
  const envelope = await getItem<ImportErrorItem[] | { errors?: ImportErrorItem[] }>(
    `/admin/imports/${jobId}/errors`,
  )
  const payload = envelope.data
  if (Array.isArray(payload)) return payload
  if (payload && Array.isArray(payload.errors)) return payload.errors
  return []
}

/* ---- Applications (AD08) ---- */

export interface ApplicationListParams extends ListParams {
  status?: ApplicationStatus
  q?: string
}

/** GET /admin/applications */
export async function listApplications(
  params: ApplicationListParams = {},
): Promise<PageEnvelope<ApplicationItem>> {
  return getPage<ApplicationItem>('/admin/applications', { params: cleanParams({ ...params }) })
}

/** POST /admin/applications/{id}/approve */
export async function approveApplication(
  applicationId: number,
  payload: ApproveApplicationPayload,
): Promise<ApproveResult> {
  const envelope = await postItem<ApproveResult>(
    `/admin/applications/${applicationId}/approve`,
    payload,
  )
  return envelope.data
}

/** POST /admin/applications/{id}/reject */
export async function rejectApplication(
  applicationId: number,
  reason: string,
): Promise<ApplicationItem> {
  const envelope = await postItem<ApplicationItem>(
    `/admin/applications/${applicationId}/reject`,
    { reason },
  )
  return envelope.data
}

/* ---- Users (AD08) ---- */

export interface UserListParams extends ListParams {
  role?: string
  status?: string
  q?: string
}

/** GET /admin/users */
export async function listUsers(params: UserListParams = {}): Promise<PageEnvelope<AdminUser>> {
  return getPage<AdminUser>('/admin/users', { params: cleanParams({ ...params }) })
}

/** PATCH /admin/users/{id} */
export async function updateUser(
  userId: number,
  payload: UserPatchPayload,
): Promise<AdminUser> {
  const envelope = await patchItem<AdminUser>(`/admin/users/${userId}`, payload)
  return envelope.data
}

/* ---- Audit logs (AD07) ---- */

/** GET /admin/audit-logs */
export async function listAuditLogs(params: AuditLogQuery = {}): Promise<PageEnvelope<AuditLog>> {
  return getPage<AuditLog>('/admin/audit-logs', { params: cleanParams({ ...params }) })
}
