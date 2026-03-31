<template>
  <section class="stack-lg">
    <article class="panel stack">
      <h2>绑定邮箱</h2>
      <p class="muted" v-if="auth.user.email">当前绑定邮箱：{{ auth.user.email }}</p>
      <p class="muted" v-else>当前未绑定邮箱，绑定后可通过邮箱验证码找回密码。</p>

      <div v-if="auth.user.email && !showBindingForm" class="stack">
        <p class="muted">如需更换绑定邮箱，请点击下方按钮。</p>
        <button class="ghost" type="button" @click="showBindingForm = true">我要换绑邮箱</button>
      </div>

      <form v-if="showBindingForm" class="stack" @submit.prevent="bindEmailByCode">
        <label>
          邮箱
          <input v-model.trim="form.email" type="email" placeholder="请输入邮箱" required />
        </label>

        <div class="row">
          <label class="grow">
            验证码
            <input v-model.trim="form.code" type="text" maxlength="6" placeholder="请输入6位验证码" required />
          </label>
          <button class="ghost" type="button" @click="sendBindCode" :disabled="loading">
            {{ loading ? '发送中...' : '发送验证码' }}
          </button>
        </div>

        <button class="primary" :disabled="loading">{{ loading ? '处理中...' : '确认绑定' }}</button>
        <button
          v-if="auth.user.email"
          class="ghost"
          type="button"
          :disabled="loading"
          @click="cancelRebind"
        >
          取消换绑
        </button>
      </form>

      <p v-if="message" class="ok">{{ message }}</p>
      <p v-if="error" class="error">{{ error }}</p>
    </article>
  </section>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'

import { api } from '../api'
import { authState } from '../stores/auth'

const auth = authState
const loading = ref(false)
const error = ref('')
const message = ref('')
const showBindingForm = ref(true)

const form = reactive({
  email: '',
  code: '',
})

const syncLocalUserEmail = (email) => {
  auth.user.email = email
  sessionStorage.setItem('exam_user', JSON.stringify(auth.user))
}

const sendBindCode = async () => {
  loading.value = true
  error.value = ''
  message.value = ''
  try {
    const resp = await api.post('/auth/email/send-bind-code/', { email: form.email })
    message.value = resp?.data?.message || '验证码已发送'
  } catch (err) {
    error.value = err?.response?.data?.error || '发送验证码失败'
  } finally {
    loading.value = false
  }
}

const bindEmailByCode = async () => {
  loading.value = true
  error.value = ''
  message.value = ''
  try {
    const resp = await api.post('/auth/email/bind/', {
      email: form.email,
      code: form.code,
    })
    const email = resp?.data?.email || form.email
    syncLocalUserEmail(email)
    message.value = '邮箱绑定成功'
    form.code = ''
  } catch (err) {
    error.value = err?.response?.data?.error || '绑定失败，请检查验证码'
  } finally {
    loading.value = false
  }
}

const cancelRebind = () => {
  form.email = auth.user.email || ''
  form.code = ''
  error.value = ''
  message.value = ''
  showBindingForm.value = false
}

onMounted(() => {
  form.email = auth.user.email || ''
  showBindingForm.value = !auth.user.email
})
</script>

<style scoped>
.row {
  display: flex;
  gap: 0.6rem;
  align-items: end;
}

.grow {
  flex: 1;
}

.ok {
  color: #117733;
  font-weight: 700;
}

.error {
  color: var(--danger);
  font-weight: 700;
}
</style>
