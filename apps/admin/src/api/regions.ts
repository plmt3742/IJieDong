import { cleanParams, getPage } from './http'
import type { PageEnvelope, Region } from './types'

export interface RegionQuery {
  level?: string
  q?: string
  parent_id?: number
  parent_code?: string
  category?: string
  enabled?: boolean
  page?: number
  page_size?: number
}

/** GET /regions */
export async function listRegions(query: RegionQuery = {}): Promise<PageEnvelope<Region>> {
  return getPage<Region>('/regions', { params: cleanParams({ ...query }) })
}
