import { api } from '../../services/api';
import {
  isFeatureUnavailable,
  toErrorMessage,
  toErrorRequestId,
} from '../../services/request';
import type {
  AccountRole,
  AdminApplication,
  AdminUser,
  AuditLogItem,
} from '../../types/api';
import type { IdentityView } from '../../types/models';
import { getIdentity, getUser, roleLabel as accountRoleLabel } from '../../utils/auth';
import { formatDateTime, formatStatus, maskPhone } from '../../utils/format';

interface RoleOption {
  key: string;
  label: string;
}

interface PendingView extends AdminApplication {
  statusLabel: string;
  phoneDisplay: string;
  phoneFull: string;
  submittedAtLabel: string;
  selfApproval: boolean;
}

interface UserView extends AdminUser {
  roleLabel: string;
  statusLabel: string;
  statusTone: string;
  phoneDisplay: string;
}

interface AuditView extends AuditLogItem {
  actionLabel: string;
  timeLabel: string;
  actorLabel: string;
}

Page({
  data: {
    identity: null as IdentityView | null,
    allowed: false,
    tab: 'pending' as 'pending' | 'users' | 'audit',
    pendingState: 'loading' as string,
    pending: [] as PendingView[],
    pendingLoaded: false,
    pendingLoading: false,
    selected: null as PendingView | null,
    roleOptions: [] as RoleOption[],
    selectedRole: 'viewer',
    rejectReason: '',
    submitting: false,
    usersState: 'idle' as string,
    users: [] as UserView[],
    usersLoaded: false,
    userQuery: '',
    auditState: 'idle' as string,
    audit: [] as AuditView[],
    auditLoaded: false,
    error: '',
    requestId: '',
    notice: '',
  },

  onLoad() {
    const identity = getIdentity();
    const allowed = identity.canManage;
    this.setData({ identity, allowed });
    if (allowed) {
      this.loadPending();
    } else {
      this.setData({ pendingState: 'no-permission' });
    }
  },

  switchTab(event: WechatMiniprogram.TouchEvent) {
    const tab = event.currentTarget.dataset.tab as 'pending' | 'users' | 'audit';
    if (!tab || tab === this.data.tab) {
      return;
    }
    this.setData({ tab, selected: null });
    if (tab === 'pending' && !this.data.pendingLoaded) {
      this.loadPending();
    }
    if (tab === 'users' && !this.data.usersLoaded) {
      this.loadUsers();
    }
    if (tab === 'audit' && !this.data.auditLoaded) {
      this.loadAudit();
    }
  },

  async loadPending() {
    if (!this.data.allowed) {
      return;
    }
    this.setData({ pendingState: 'loading', pendingLoading: true, error: '', requestId: '', notice: '' });
    try {
      const result = await api.admin.applications({ status: 'pending', page_size: 20 });
      const pending = result.items.map((item) => this.toPendingView(item));
      this.setData({
        pendingLoading: false,
        pendingLoaded: true,
        pending,
        pendingState: pending.length ? 'ready' : 'empty',
      });
    } catch (error) {
      if (isFeatureUnavailable(error)) {
        this.setData({
          pendingLoading: false,
          pendingLoaded: true,
          pending: [],
          pendingState: 'empty',
          notice: '管理接口尚未就绪。后端实现后，此处将显示待审批申请。',
        });
        return;
      }
      this.setData({
        pendingLoading: false,
        pendingState: 'error',
        error: toErrorMessage(error),
        requestId: toErrorRequestId(error),
      });
    }
  },

  toPendingView(item: AdminApplication): PendingView {
    const phoneDisplay = item.phone_masked || maskPhone(item.phone);
    const user = getUser();
    const samePhone = !!(user && user.phone && item.phone && user.phone === item.phone);
    return {
      ...item,
      statusLabel: formatStatus(item.status),
      phoneDisplay,
      phoneFull: item.phone || '',
      submittedAtLabel: formatDateTime(item.submitted_at),
      selfApproval: item.is_self === true || samePhone,
    };
  },

  openApplication(event: WechatMiniprogram.TouchEvent) {
    const index = Number(event.currentTarget.dataset.index);
    const application = this.data.pending[index];
    if (!application) {
      return;
    }
    const identity = this.data.identity;
    const options: RoleOption[] =
      identity && identity.isAdmin
        ? [
            { key: 'viewer', label: '查看者（默认）' },
            { key: 'editor', label: '编辑者' },
            { key: 'approver', label: '审批者' },
            { key: 'admin', label: '管理员' },
          ]
        : [{ key: 'viewer', label: '查看者（默认）' }];
    this.setData({
      selected: application,
      selectedRole: 'viewer',
      rejectReason: '',
      roleOptions: options,
    });
  },

  closeDetail() {
    this.setData({ selected: null, rejectReason: '' });
  },

  selectRole(event: WechatMiniprogram.TouchEvent) {
    const role = String(event.currentTarget.dataset.role || '');
    if (!role) {
      return;
    }
    const allowed = this.data.roleOptions.some((option) => option.key === role);
    if (!allowed) {
      wx.showToast({ title: '当前角色不能分配该角色', icon: 'none' });
      return;
    }
    this.setData({ selectedRole: role });
  },

  handleRejectInput(event: WechatMiniprogram.Input) {
    this.setData({ rejectReason: event.detail.value });
  },

  approve() {
    const selected = this.data.selected;
    if (!selected || this.data.submitting) {
      return;
    }
    if (selected.selfApproval) {
      wx.showToast({ title: '不能审批本人申请', icon: 'none' });
      return;
    }
    wx.showModal({
      title: '批准申请',
      content: `批准 ${selected.display_name} 的申请，角色为 ${accountRoleLabel(this.data.selectedRole as AccountRole)}。`,
      confirmText: '批准',
      success: (result) => {
        if (result.confirm) {
          this.doApprove(selected);
        }
      },
    });
  },

  async doApprove(selected: PendingView) {
    this.setData({ submitting: true });
    try {
      await api.admin.approve(selected.id, {
        role: this.data.selectedRole,
        unit: selected.unit,
        note: '小程序审批',
      });
      this.setData({ submitting: false, selected: null });
      wx.showToast({ title: '已批准', icon: 'success' });
      this.loadPending();
      this.loadAudit();
    } catch (error) {
      this.setData({ submitting: false });
      wx.showModal({
        title: '审批失败',
        content: toErrorMessage(error),
        showCancel: false,
        confirmText: '知道了',
      });
      if (isFeatureUnavailable(error)) {
        this.loadPending();
      }
    }
  },

  reject() {
    const selected = this.data.selected;
    if (!selected || this.data.submitting) {
      return;
    }
    if (selected.selfApproval) {
      wx.showToast({ title: '不能审批本人申请', icon: 'none' });
      return;
    }
    const reason = this.data.rejectReason.trim();
    if (reason.length < 5 || reason.length > 200) {
      wx.showToast({ title: '驳回原因需 5 至 200 字', icon: 'none' });
      return;
    }
    wx.showModal({
      title: '驳回申请',
      content: '驳回后申请者可在冷却期后重新提交。确认驳回？',
      confirmText: '驳回',
      success: (result) => {
        if (result.confirm) {
          this.doReject(selected, reason);
        }
      },
    });
  },

  async doReject(selected: PendingView, reason: string) {
    this.setData({ submitting: true });
    try {
      await api.admin.reject(selected.id, { reason });
      this.setData({ submitting: false, selected: null, rejectReason: '' });
      wx.showToast({ title: '已驳回', icon: 'success' });
      this.loadPending();
      this.loadAudit();
    } catch (error) {
      this.setData({ submitting: false });
      wx.showModal({
        title: '驳回失败',
        content: toErrorMessage(error),
        showCancel: false,
        confirmText: '知道了',
      });
    }
  },

  async loadUsers() {
    if (!this.data.allowed) {
      return;
    }
    this.setData({ usersState: 'loading', error: '', requestId: '', notice: '' });
    try {
      const result = await api.admin.users({ q: this.data.userQuery || undefined, page_size: 20 });
      const users = result.items.map((item) => this.toUserView(item));
      this.setData({
        usersLoaded: true,
        users,
        usersState: users.length ? 'ready' : 'empty',
      });
    } catch (error) {
      if (isFeatureUnavailable(error)) {
        this.setData({
          usersLoaded: true,
          users: [],
          usersState: 'empty',
          notice: '用户管理接口尚未就绪。',
        });
        return;
      }
      this.setData({
        usersState: 'error',
        error: toErrorMessage(error),
        requestId: toErrorRequestId(error),
      });
    }
  },

  toUserView(item: AdminUser): UserView {
    return {
      ...item,
      roleLabel: accountRoleLabel(item.role),
      statusLabel: formatStatus(item.status),
      statusTone: item.status === 'active' ? 'success' : 'danger',
      phoneDisplay: item.phone_masked || '',
    };
  },

  handleUserQuery(event: WechatMiniprogram.Input) {
    this.setData({ userQuery: event.detail.value });
  },

  searchUsers() {
    this.loadUsers();
  },

  toggleUserStatus(event: WechatMiniprogram.TouchEvent) {
    const index = Number(event.currentTarget.dataset.index);
    const user = this.data.users[index];
    if (!user || this.data.submitting) {
      return;
    }
    const nextStatus = user.status === 'active' ? 'disabled' : 'active';
    wx.showModal({
      title: nextStatus === 'disabled' ? '禁用用户' : '启用用户',
      content: `${user.display_name} 将切换为${formatStatus(nextStatus)}。角色不变。`,
      confirmText: nextStatus === 'disabled' ? '禁用' : '启用',
      success: (result) => {
        if (result.confirm) {
          this.doUpdateUser(user, nextStatus);
        }
      },
    });
  },

  async doUpdateUser(user: UserView, status: 'active' | 'disabled') {
    this.setData({ submitting: true });
    try {
      const updated = await api.admin.updateUser(user.id, { status });
      const users = this.data.users.map((item) =>
        item.id === user.id
          ? {
              ...item,
              ...updated,
              roleLabel: accountRoleLabel(updated.role),
              statusLabel: formatStatus(updated.status),
              statusTone: updated.status === 'active' ? 'success' : 'danger',
            }
          : item
      );
      this.setData({ submitting: false, users });
      wx.showToast({ title: '状态已更新', icon: 'success' });
      this.loadAudit();
    } catch (error) {
      this.setData({ submitting: false });
      wx.showModal({
        title: '更新失败',
        content: toErrorMessage(error),
        showCancel: false,
        confirmText: '知道了',
      });
    }
  },

  async loadAudit() {
    if (!this.data.allowed) {
      return;
    }
    this.setData({ auditState: 'loading' });
    try {
      const items = await api.admin.auditLogs(10);
      const audit = items.map((item) => ({
        ...item,
        actionLabel: actionLabel(item.action),
        timeLabel: formatDateTime(item.created_at),
        actorLabel: item.actor_name || item.actor || '系统',
      }));
      this.setData({ auditLoaded: true, audit, auditState: audit.length ? 'ready' : 'empty' });
    } catch (error) {
      if (isFeatureUnavailable(error)) {
        this.setData({
          auditLoaded: true,
          audit: [],
          auditState: 'empty',
          notice: '审计接口尚未就绪。',
        });
        return;
      }
      this.setData({
        auditState: 'error',
        error: toErrorMessage(error),
        requestId: toErrorRequestId(error),
      });
    }
  },

  onRetry() {
    if (this.data.tab === 'pending') {
      this.loadPending();
    } else if (this.data.tab === 'users') {
      this.loadUsers();
    } else {
      this.loadAudit();
    }
  },

  goProfile() {
    wx.switchTab({ url: '/pages/profile/profile' });
  },
});

function actionLabel(action: string): string {
  const labels: Record<string, string> = {
    'application.submit': '提交申请',
    'application.approve': '批准申请',
    'application.reject': '驳回申请',
    'application.resubmit': '重新提交',
    'user.activate': '激活账号',
    'user.disable': '禁用账号',
    'user.enable': '启用账号',
    'user.role_change': '变更角色',
    'export.create': '创建导出',
  };
  return labels[action] || action;
}
