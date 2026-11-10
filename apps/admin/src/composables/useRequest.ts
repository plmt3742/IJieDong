import { ref, type Ref } from 'vue'

import { ApiError, toApiError } from '@/api/http'

export interface RequestState<T> {
  data: Ref<T | null>
  loading: Ref<boolean>
  error: Ref<ApiError | null>
  run: () => Promise<void>
}

/**
 * Minimal async loader with stale-response protection: only the latest call
 * may write state, so filter changes cannot be overwritten by a late reply.
 */
export function useRequest<T>(loader: () => Promise<T>): RequestState<T> {
  const data = ref<T | null>(null) as Ref<T | null>
  const loading = ref(false)
  const error = ref<ApiError | null>(null)
  let ticket = 0

  async function run(): Promise<void> {
    const current = ++ticket
    loading.value = true
    error.value = null
    try {
      const result = await loader()
      if (current === ticket) data.value = result
    } catch (caught) {
      if (current === ticket) error.value = toApiError(caught)
    } finally {
      if (current === ticket) loading.value = false
    }
  }

  return { data, loading, error, run }
}
