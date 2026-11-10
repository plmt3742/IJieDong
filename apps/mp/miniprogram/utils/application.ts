import type {
  ApplicationStatusResponse,
  ApplicationTimelineItem,
} from '../types/api';
import { formatDateTime } from './format';

export function buildApplicationTimeline(
  application: ApplicationStatusResponse
): ApplicationTimelineItem[] {
  const status = application.status;
  const submitted: ApplicationTimelineItem = {
    key: 'submitted',
    label: '已提交',
    time: formatDateTime(application.submitted_at),
    state: 'done',
  };
  let reviewState: ApplicationTimelineItem['state'] = 'pending';
  if (status === 'pending') {
    reviewState = 'current';
  } else if (status === 'approved' || status === 'rejected' || status === 'active') {
    reviewState = 'done';
  }
  const review: ApplicationTimelineItem = {
    key: 'review',
    label: '审核中',
    time: application.reviewed_at ? formatDateTime(application.reviewed_at) : '',
    state: reviewState,
  };
  let result: ApplicationTimelineItem;
  if (status === 'rejected') {
    result = {
      key: 'result',
      label: '已驳回',
      time: application.reviewed_at ? formatDateTime(application.reviewed_at) : '',
      state: 'failed',
      description: application.reject_reason || '',
    };
  } else if (status === 'approved' || status === 'active') {
    result = {
      key: 'result',
      label: '已批准',
      time: application.reviewed_at ? formatDateTime(application.reviewed_at) : '',
      state: 'done',
    };
  } else {
    result = {
      key: 'result',
      label: '待审批结果',
      time: '',
      state: 'pending',
    };
  }
  return [submitted, review, result];
}

export function canResubmit(application: ApplicationStatusResponse | null): boolean {
  if (!application || application.status !== 'rejected') {
    return false;
  }
  const attempts = application.resubmit_count || 0;
  if (attempts >= 3) {
    return false;
  }
  if (!application.resubmit_available_at) {
    return true;
  }
  const availableAt = new Date(application.resubmit_available_at).getTime();
  if (Number.isNaN(availableAt)) {
    return true;
  }
  return availableAt <= Date.now();
}

export function resubmitHint(application: ApplicationStatusResponse | null): string {
  if (!application || application.status !== 'rejected') {
    return '';
  }
  if ((application.resubmit_count || 0) >= 3) {
    return '重提次数已达上限，请联系管理员处理。';
  }
  if (canResubmit(application)) {
    return '已过冷却时间，可修改申请说明后重新提交。';
  }
  return application.resubmit_available_at
    ? `可于 ${formatDateTime(application.resubmit_available_at)} 后重提。`
    : '驳回后 24 小时内不可重提。';
}
