<script setup lang="ts">
import { Key, User } from '@element-plus/icons-vue'
import type { FormInstance, FormRules } from 'element-plus'
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { ApiError, describeApiError } from '@/api/http'
import { useAuthStore } from '@/stores/auth'

interface LoginForm {
  username: string
  password: string
}

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()

const formRef = ref<FormInstance>()
const form = reactive<LoginForm>({ username: '', password: '' })
const errorMessage = ref('')
const errorDetail = ref('')

const rules: FormRules<LoginForm> = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 4, max: 32, message: '用户名长度为 4 到 32 个字符', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码至少 6 个字符', trigger: 'blur' },
  ],
}

async function handleSubmit(): Promise<void> {
  if (!formRef.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  errorMessage.value = ''
  errorDetail.value = ''
  try {
    await auth.login({ username: form.username.trim(), password: form.password })
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/overview'
    await router.replace(redirect)
  } catch (caught) {
    const apiError = caught instanceof ApiError ? caught : null
    if (apiError && apiError.status === 401) {
      errorMessage.value = '用户名或密码不正确，请重新输入'
    } else {
      errorMessage.value = describeApiError(caught)
    }
    errorDetail.value = apiError
      ? `HTTP ${apiError.status || '-'} · ${apiError.code}${
          apiError.requestId ? ` · request_id ${apiError.requestId}` : ''
        }`
      : ''
  }
}
</script>

<template>
  <div class="login-page">
    <section class="login-brand" aria-hidden="true">
      <div class="login-brand__inner">
        <p class="login-brand__mark">i揭东</p>
        <h1 class="login-brand__title">区情数据管理后台</h1>
        <p class="login-brand__description">
          面向数据维护人员与管理员：导入合成演示数据、核对数据值、审批账号申请并查看审计记录。
        </p>
        <dl class="login-brand__facts">
          <div>
            <dt>数据范围</dt>
            <dd>区 / 镇街 / 村居三级</dd>
          </div>
          <div>
            <dt>数据时点</dt>
            <dd>2025 年度演示数据</dd>
          </div>
          <div>
            <dt>环境</dt>
            <dd>Demo v0 演示环境</dd>
          </div>
        </dl>
      </div>
      <p class="login-brand__foot">合成演示数据，不含真实业务数据。</p>
    </section>

    <section class="login-panel">
      <div class="login-card">
        <header class="login-card__header">
          <h2 class="login-card__title">登录管理后台</h2>
          <p class="login-card__subtitle">请使用管理员发放的账号登录</p>
        </header>

        <el-alert
          v-if="errorMessage"
          class="login-card__alert"
          :title="errorMessage"
          :description="errorDetail"
          type="error"
          :closable="false"
          show-icon
        />

        <el-form
          ref="formRef"
          :model="form"
          :rules="rules"
          label-position="top"
          size="large"
          @submit.prevent="handleSubmit"
        >
          <el-form-item label="用户名" prop="username">
            <el-input
              v-model="form.username"
              :prefix-icon="User"
              name="username"
              autocomplete="username"
              placeholder="请输入用户名"
              clearable
            />
          </el-form-item>

          <el-form-item label="密码" prop="password">
            <el-input
              v-model="form.password"
              :prefix-icon="Key"
              name="password"
              type="password"
              autocomplete="current-password"
              placeholder="请输入密码"
              show-password
              @keyup.enter="handleSubmit"
            />
          </el-form-item>

          <el-button
            class="login-card__submit"
            type="primary"
            size="large"
            :loading="auth.submitting"
            native-type="submit"
          >
            登录
          </el-button>
        </el-form>

        <p class="login-card__hint">
          忘记密码或需要新账号，请联系数据管理员处理，演示环境不提供自助注册。
        </p>
      </div>
    </section>
  </div>
</template>

<style scoped>
.login-page {
  display: grid;
  grid-template-columns: minmax(360px, 1fr) minmax(420px, 520px);
  min-height: 100vh;
  background: var(--gov-bg);
}

.login-brand {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: var(--gov-space-8);
  background-color: var(--gov-primary-active);
  background-image:
    linear-gradient(rgba(255, 255, 255, 0.05) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.05) 1px, transparent 1px);
  background-size: 32px 32px;
  color: var(--gov-text-inverse);
}

.login-brand__inner {
  max-width: 460px;
  margin-top: 12vh;
}

.login-brand__mark {
  font-size: var(--gov-text-lg);
  font-weight: 600;
  letter-spacing: 0.12em;
  opacity: 0.86;
}

.login-brand__title {
  margin-top: var(--gov-space-3);
  font-size: 30px;
  font-weight: 600;
  line-height: 1.25;
}

.login-brand__description {
  margin-top: var(--gov-space-4);
  font-size: var(--gov-text-sm);
  line-height: 1.7;
  color: rgba(255, 255, 255, 0.82);
}

.login-brand__facts {
  display: flex;
  flex-wrap: wrap;
  gap: var(--gov-space-6);
  margin-top: var(--gov-space-8);
  padding-top: var(--gov-space-4);
  border-top: 1px solid rgba(255, 255, 255, 0.2);
}

.login-brand__facts dt {
  font-size: var(--gov-text-xs);
  color: rgba(255, 255, 255, 0.62);
}

.login-brand__facts dd {
  margin: 2px 0 0;
  font-size: var(--gov-text-sm);
  color: rgba(255, 255, 255, 0.92);
}

.login-brand__foot {
  font-size: var(--gov-text-xs);
  color: rgba(255, 255, 255, 0.55);
}

.login-panel {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--gov-space-6);
}

.login-card {
  width: 100%;
  max-width: 380px;
  padding: var(--gov-space-8);
  background: var(--gov-surface);
  border: 1px solid var(--gov-border);
  border-radius: var(--gov-radius-md);
  box-shadow: var(--gov-shadow-raised);
}

.login-card__header {
  margin-bottom: var(--gov-space-5);
}

.login-card__title {
  font-size: var(--gov-text-xl);
  font-weight: 600;
  line-height: var(--gov-line-tight);
}

.login-card__subtitle {
  margin-top: var(--gov-space-1);
  font-size: var(--gov-text-sm);
  color: var(--gov-text-secondary);
}

.login-card__alert {
  margin-bottom: var(--gov-space-4);
}

.login-card__submit {
  width: 100%;
  margin-top: var(--gov-space-2);
}

.login-card__hint {
  margin-top: var(--gov-space-4);
  padding-top: var(--gov-space-3);
  border-top: 1px solid var(--gov-border);
  font-size: var(--gov-text-xs);
  color: var(--gov-text-muted);
  line-height: 1.7;
}

@media (max-width: 900px) {
  .login-page {
    grid-template-columns: 1fr;
  }

  .login-brand {
    display: none;
  }

  .login-panel {
    padding: var(--gov-space-4);
  }

  .login-card {
    padding: var(--gov-space-5);
  }
}
</style>
