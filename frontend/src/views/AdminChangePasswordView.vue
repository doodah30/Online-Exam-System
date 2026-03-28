<template>
  <section class="stack-lg">
    <article class="panel row-between">
      <div>
        <h2>修改我的密码</h2>
        <p class="muted">管理员专用：使用旧密码校验后更新新密码。</p>
      </div>
      <button class="ghost" @click="goAdminHome">返回管理员控制台</button>
    </article>

    <article class="panel stack">
      <div class="grid two-col">
        <label>
          旧密码
          <div class="password-field">
            <input
              class="password-input"
              v-model="form.old_password"
              :type="showOld ? 'text' : 'password'"
              placeholder="请输入当前密码"
            />
            <button class="toggle-btn" type="button" @click="showOld = !showOld">
              {{ showOld ? '隐藏' : '显示' }}
            </button>
          </div>
        </label>

        <label>
          新密码
          <div class="password-field">
            <input
              class="password-input"
              v-model="form.new_password"
              :type="showNew ? 'text' : 'password'"
              placeholder="请输入新密码（至少6位）"
            />
            <button class="toggle-btn" type="button" @click="showNew = !showNew">
              {{ showNew ? '隐藏' : '显示' }}
            </button>
          </div>
        </label>
      </div>

      <div class="row-wrap">
        <button class="primary" @click="submit">确认修改</button>
      </div>

      <p v-if="success" class="ok">{{ success }}</p>
      <p v-if="error" class="error">{{ error }}</p>
    </article>
  </section>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

import { api } from '../api'
import { setAuth } from '../stores/auth'

const router = useRouter()
const showOld = ref(false)
const showNew = ref(false)
const error = ref('')
const success = ref('')

const form = reactive({
  old_password: '',
  new_password: '',
})

const goAdminHome = () => router.push('/admin')

const submit = async () => {
  error.value = ''
  success.value = ''
  try {
    const res = await api.post('/admin/me/change-password/', {
      old_password: form.old_password,
      new_password: form.new_password,
    })
    setAuth(res.data)
    form.old_password = ''
    form.new_password = ''
    success.value = '密码修改成功，当前登录已更新。'
  } catch (err) {
    error.value = err?.response?.data?.error || '修改密码失败'
  }
}
</script>

<style scoped>
.error {
  color: var(--danger);
  font-weight: 700;
}

.ok {
  color: var(--ok);
  font-weight: 700;
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
