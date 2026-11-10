import { cleanParams, getItem, getList } from './http'
import type { Indicator } from './types'

export interface IndicatorQuery {
  level?: string
  category?: string
  value_type?: string
  enabled?: boolean
}

/** GET /indicators */
export async function listIndicators(query: IndicatorQuery = {}): Promise<Indicator[]> {
  const envelope = await getList<Indicator>('/indicators', {
    params: cleanParams({ enabled: true, ...query }),
  })
  return envelope.data
}

/** GET /indicators/{id} */
export async function getIndicator(indicatorId: number): Promise<Indicator> {
  const envelope = await getItem<Indicator>(`/indicators/${indicatorId}`)
  return envelope.data
}
