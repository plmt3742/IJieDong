import { cleanParams, getPage } from './http'
import type { DataValue, DataValueQuery, PageEnvelope } from './types'

/** GET /data-values - published rows only, as served by B04. */
export async function listDataValues(query: DataValueQuery = {}): Promise<PageEnvelope<DataValue>> {
  return getPage<DataValue>('/data-values', {
    params: cleanParams({ status: 'published', ...query }),
  })
}
