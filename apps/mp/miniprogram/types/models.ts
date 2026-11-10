/** View models used by pages and components. */
import type {
  AnswerBlock,
  ApplicationStatus,
  Citation,
  UserRole,
} from './api';
import type { ChartSpec } from './chart';

export type ViewMode = 'loading' | 'ready' | 'empty' | 'error' | 'locked' | 'no-permission';

export interface MetricCardModel {
  code: string;
  label: string;
  value: number | null;
  unit: string;
  year: number;
  status: string;
  precision: number;
}

export interface RegionRowModel {
  id: number;
  code: string;
  name: string;
  level: string;
  category: string;
  parentId: number | null;
  meta: string;
  zoneTag: string;
  selectable: boolean;
}

export interface IdentityView {
  role: UserRole;
  label: string;
  name: string;
  unit: string;
  isGuest: boolean;
  isApplicant: boolean;
  isAdmin: boolean;
  isApprover: boolean;
  canExport: boolean;
  canManage: boolean;
  canUseAi: boolean;
  applicationStatus: ApplicationStatus;
  applicationNo: string;
}

export interface ChatMessageModel {
  id: string;
  role: 'user' | 'assistant';
  text: string;
  question: string;
  blocks: AnswerBlock[];
  citations: Citation[];
  followUps: string[];
  state: 'done' | 'thinking' | 'error' | 'refused';
  errorText: string;
  demo: boolean;
  hasSourceBlock: boolean;
  time: string;
}

export interface ExportFormatOption {
  key: 'png' | 'pdf' | 'xlsx' | 'csv';
  label: string;
  description: string;
  note: string;
  disabled: boolean;
}

export interface IndicatorChartBundle {
  spec: ChartSpec | null;
  tableColumns: string[];
  tableRows: Array<Array<string | number | null>>;
  label: string;
}
