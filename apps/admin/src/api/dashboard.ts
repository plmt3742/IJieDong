import { cleanParams, getItem } from './http'
import type { DashboardOverview } from './types'

/** GET /dashboard/overview */
export async function getDashboardOverview(periodYear: number): Promise<DashboardOverview> {
  const envelope = await getItem<DashboardOverview>('/dashboard/overview', {
    params: cleanParams({ period_year: periodYear }),
  })
  return envelope.data
}
