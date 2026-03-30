<template>
  <section class="grid two-col auth-page">
    <article class="panel hero-panel">
      <h2>智能在线考试平台</h2>
      <p>
        一套可直接演示的在线考试系统：支持老师出题组卷、学生在线作答、自动评分与阅卷查看。
      </p>
      <ul>
        <li>支持老师 / 学生双角色注册登录</li>
        <li>支持客观题自动阅卷并实时返回成绩</li>
        <li>支持老师查看每场考试提交记录</li>
      </ul>
      <p class="tiny muted">管理员账号不开放公开注册，由系统初始化或由现有管理员创建。</p>
    </article>

    <article class="panel form-panel">
      <div class="tabs">
        <button :class="{ active: mode === 'login' }" @click="mode = 'login'">登录</button>
        <button :class="{ active: mode === 'register' }" @click="mode = 'register'">注册</button>
      </div>

      <form class="stack" @submit.prevent="submit">
        <label>
          用户名
          <input v-model.trim="form.username" type="text" placeholder="请输入用户名" required />
        </label>

        <label>
          密码
          <div class="password-field">
            <input
              v-model="form.password"
              class="password-input"
              :type="showPassword ? 'text' : 'password'"
              placeholder="请输入密码"
              required
            />
            <button class="toggle-btn" type="button" @click="showPassword = !showPassword">
              {{ showPassword ? '隐藏' : '显示' }}
            </button>
          </div>
        </label>

        <label v-if="mode === 'register'">
          身份
          <select v-model="form.role" required>
            <option value="student">学生</option>
            <option value="teacher">老师</option>
          </select>
        </label>

        <label v-if="mode === 'register'">
          邮箱（选填，建议用于找回密码）
          <input v-model.trim="form.email" type="email" placeholder="例如：name@example.com" />
        </label>

        <button class="primary" :disabled="loading">{{ loading ? '处理中...' : modeText }}</button>
      </form>

      <p v-if="error" class="error">{{ error }}</p>

      <article class="forgot-panel stack">
        <button class="link-btn" type="button" @click="showForgot = !showForgot">
          {{ showForgot ? '收起忘记密码' : '忘记密码？用邮箱验证码找回' }}
        </button>

        <form v-if="showForgot" class="stack" @submit.prevent="resetPasswordByCode">
          <label>
            用户名
            <input v-model.trim="forgotForm.username" type="text" placeholder="请输入账号用户名" required />
          </label>

          <div class="inline-row">
            <label class="grow">
              验证码
              <input v-model.trim="forgotForm.code" type="text" maxlength="6" placeholder="6位验证码" required />
            </label>
            <button class="ghost" type="button" @click="sendResetCode" :disabled="forgotLoading">
              {{ forgotLoading ? '发送中...' : '发送验证码' }}
            </button>
          </div>

          <label>
            新密码
            <input v-model="forgotForm.newPassword" type="password" placeholder="至少6位" required />
          </label>

          <button class="primary" :disabled="forgotLoading">{{ forgotLoading ? '处理中...' : '重置并登录' }}</button>
        </form>
      </article>
    </article>
  </section>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

import { api } from '../api'
import { setAuth } from '../stores/auth'

const router = useRouter()

const mode = ref('login')
const loading = ref(false)
const error = ref('')
const showPassword = ref(false)
const showForgot = ref(false)
const forgotLoading = ref(false)

const form = reactive({
  username: '',
  password: '',
  role: 'student',
  email: '',
})

const forgotForm = reactive({
  username: '',
  code: '',
  newPassword: '',
})

const modeText = computed(() => (mode.value === 'login' ? '登录' : '注册并登录'))

const submit = async () => {
  error.value = ''
  loading.value = true

  try {
    let response
    if (mode.value === 'register') {
      response = await api.post('/auth/register/', {
        username: form.username,
        password: form.password,
        role: form.role,
        email: form.email,
      })
    } else {
      response = await api.post('/auth/login/', {
        username: form.username,
        password: form.password,
      })
    }

    setAuth(response.data)
    if (response.data.user.role === 'teacher') {
      router.push('/teacher')
    } else if (response.data.user.role === 'admin') {
      router.push('/admin')
    } else {
      router.push('/dashboard')
    }
  } catch (err) {
    error.value = err?.response?.data?.error || '请求失败，请确认后端已启动'
  } finally {
    loading.value = false
  }
}

const sendResetCode = async () => {
  error.value = ''
  forgotLoading.value = true
  try {
    const resp = await api.post('/auth/password-reset/send-code/', {
      username: forgotForm.username,
    })
    error.value = resp?.data?.message || '验证码已发送，请查收邮箱'
  } catch (err) {
    error.value = err?.response?.data?.error || '发送验证码失败'
  } finally {
    forgotLoading.value = false
  }
}

const resetPasswordByCode = async () => {
  error.value = ''
  forgotLoading.value = true
  try {
    const response = await api.post('/auth/password-reset/confirm/', {
      username: forgotForm.username,
      code: forgotForm.code,
      new_password: forgotForm.newPassword,
    })
    setAuth(response.data)
    if (response.data.user.role === 'teacher') {
      router.push('/teacher')
    } else if (response.data.user.role === 'admin') {
      router.push('/admin')
    } else {
      router.push('/dashboard')
    }
  } catch (err) {
    error.value = err?.response?.data?.error || '重置失败，请检查验证码'
  } finally {
    forgotLoading.value = false
  }
}
</script>

<style scoped>
.auth-page {
  margin-top: 1.2rem;
}

.hero-panel h2 {
  font-size: clamp(1.5rem, 3vw, 2rem);
  margin-bottom: 0.8rem;
}

.hero-panel p {
  color: var(--muted);
  margin-bottom: 1rem;
}

.hero-panel ul {
  list-style: none;
  display: grid;
  gap: 0.65rem;
}

.hero-panel li {
  background: var(--soft);
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 0.7rem 0.9rem;
}

.form-panel {
  display: grid;
  gap: 1rem;
}

.tabs {
  display: inline-flex;
  background: var(--soft);
  padding: 0.2rem;
  border-radius: 999px;
  border: 1px solid var(--line);
}

.tabs button {
  border: none;
  background: transparent;
  padding: 0.4rem 0.9rem;
  border-radius: 999px;
  cursor: pointer;
  font-weight: 600;
}

.tabs button.active {
  background: white;
  box-shadow: var(--shadow-sm);
}

.error {
  color: var(--danger);
  font-weight: 600;
}

.forgot-panel {
  border-top: 1px dashed var(--line);
  padding-top: 0.8rem;
}

.link-btn {
  border: none;
  background: transparent;
  text-align: left;
  color: var(--brand-deep);
  font-weight: 700;
  padding: 0;
  cursor: pointer;
}

.inline-row {
  display: flex;
  gap: 0.6rem;
  align-items: end;
}

.grow {
  flex: 1;
}

.password-field {
  position: relative;
}

.password-input {
  padding-right: 4.2rem;
}

.toggle-btn {
  position: absolute;
  right: 0.4rem;
  top: 50%;
  transform: translateY(-50%);
  border: none;
  background: transparent;
  color: var(--brand-deep);
  padding: 0.2rem 0.35rem;
  font-size: 0.82rem;
  font-weight: 700;
}

.password-input::-ms-reveal,
.password-input::-ms-clear {
  display: none;
}
</style>
