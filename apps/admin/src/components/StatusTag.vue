<script setup lang="ts">
import { computed } from 'vue'

import {
  APPLICATION_STATUS_LABELS,
  APPLICATION_STATUS_TAG_TYPES,
  IMPORT_STATUS_LABELS,
  IMPORT_STATUS_TAG_TYPES,
  PUBLISH_STATUS_LABELS,
  QUALITY_LABELS,
  QUALITY_TAG_TYPES,
  ROLE_LABELS,
  USER_STATUS_LABELS,
} from '@/utils/format'

type TagType = 'success' | 'info' | 'warning' | 'danger' | ''

interface Props {
  kind: 'quality' | 'publish' | 'import' | 'application' | 'user' | 'role'
  value: string | null | undefined
}

const props = defineProps<Props>()

const normalized = computed(() => (props.value ?? '').trim())

const label = computed(() => {
  const value = normalized.value
  if (!value) return '—'
  switch (props.kind) {
    case 'quality':
      return QUALITY_LABELS[value] ?? value
    case 'publish':
      return PUBLISH_STATUS_LABELS[value] ?? value
    case 'import':
      return IMPORT_STATUS_LABELS[value] ?? value
    case 'application':
      return APPLICATION_STATUS_LABELS[value] ?? value
    case 'user':
      return USER_STATUS_LABELS[value] ?? value
    case 'role':
      return ROLE_LABELS[value] ?? value
    default:
      return value
  }
})

const type = computed<TagType>(() => {
  const value = normalized.value
  switch (props.kind) {
    case 'quality':
      return QUALITY_TAG_TYPES[value] ?? 'info'
    case 'import':
      return IMPORT_STATUS_TAG_TYPES[value] ?? 'info'
    case 'application':
      return APPLICATION_STATUS_TAG_TYPES[value] ?? 'info'
    case 'user':
      return value === 'active' ? 'success' : value === 'disabled' ? 'danger' : 'info'
    case 'role':
      return value === 'admin' || value === 'approver' ? 'warning' : 'info'
    default:
      return 'info'
  }
})
</script>

<template>
  <el-tag size="small" effect="light" :type="type">{{ label }}</el-tag>
</template>
