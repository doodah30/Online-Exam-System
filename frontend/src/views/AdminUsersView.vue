<template>
  <section class="stack-lg">
    <article class="panel row-between">
      <div>
        <h2>用户管理</h2>
        <p class="muted">管理管理员、老师、学生账号与可用状态。</p>
      </div>
      <button class="ghost" @click="goAdminHome">返回管理员控制台</button>
    </article>

    <article class="panel stack">
      <h3>新增用户</h3>
      <div class="grid two-col">
        <label>
          用户名
          <input v-model.trim="createForm.username" />
        </label>
        <label>
          初始密码
          <div class="password-field">
            <input
              v-model="createForm.password"
              class="password-input"
              :type="showCreatePassword ? 'text' : 'password'"
            />
            <button class="toggle-btn" type="button" @click="showCreatePassword = !showCreatePassword">
              {{ showCreatePassword ? '隐藏' : '显示' }}
            </button>
          </div>
        </label>
      </div>
      <div class="grid two-col">
        <label>
          角色
          <select v-model="createForm.role">
            <option value="student">学生</option>
            <option value="teacher">老师</option>
            <option value="admin">管理员</option>
          </select>
        </label>
        <label>
          账号状态
          <select v-model="createForm.is_active">
            <option :value="true">启用</option>
            <option :value="false">禁用</option>
          </select>
        </label>
      </div>
      <div class="row-wrap">
        <button class="primary" @click="createUser">创建用户</button>
      </div>
    </article>

    <article class="panel stack">
      <div class="row-between">
        <h3>用户列表</h3>
        <div class="row-wrap">
          <input class="mini" v-model.trim="filters.q" placeholder="按用户名搜索" />
          <select v-model="filters.role">
            <option value="">全部角色</option>
            <option value="admin">管理员</option>
            <option value="teacher">老师</option>
            <option value="student">学生</option>
          </select>
          <button class="ghost" @click="loadUsers">查询</button>
        </div>
      </div>

      <p v-if="loading" class="muted">加载中...</p>
      <p v-else-if="users.length === 0" class="muted">没有符合条件的用户</p>

      <div v-else class="stack-sm">
        <div v-for="item in users" :key="item.id" class="card stack-sm">
          <div class="row-between">
            <h4>#{{ item.id }} {{ item.username }}</h4>
            <span class="tiny">{{ item.role }} · {{ item.is_active ? '启用' : '禁用' }}</span>
          </div>

          <div class="grid two-col">
            <label>
              用户名
              <input v-model.trim="editForms[item.id].username" :disabled="isSelf(item)" />
            </label>
            <label>
              角色
              <select v-model="editForms[item.id].role" :disabled="isSelf(item)">
                <option value="admin">管理员</option>
                <option value="teacher">老师</option>
                <option value="student">学生</option>
              </select>
            </label>
          </div>

          <div class="row-wrap">
            <label class="inline-check">
              <input type="checkbox" v-model="editForms[item.id].is_active" :disabled="isSelf(item)" />
              <span>启用账号</span>
            </label>
            <button class="ghost" :disabled="isSelf(item)" @click="updateUser(item.id)">保存修改</button>
            <button class="ghost" :disabled="isSelf(item)" @click="toggleUser(item)">{{ item.is_active ? '禁用' : '启用' }}</button>
            <button class="ghost" :disabled="isSelf(item)" @click="openReset(item.id)">重置密码</button>
            <button class="danger-btn" :disabled="isSelf(item)" @click="removeUser(item)">删除</button>
            <span v-if="isSelf(item)" class="tiny">当前账号不可被自身修改/禁用/删除/重置密码</span>
          </div>

          <div v-if="resetTargetId === item.id" class="row-wrap">
            <div class="password-field mini-wrap">
              <input
                class="mini password-input"
                v-model="newPassword"
                :type="showResetPassword ? 'text' : 'password'"
                placeholder="新密码（至少6位）"
              />
              <button class="toggle-btn" type="button" @click="showResetPassword = !showResetPassword">
                {{ showResetPassword ? '隐藏' : '显示' }}
              </button>
            </div>
            <button class="ghost" @click="resetPassword(item.id)">确认重置</button>
            <button class="ghost" @click="closeReset">取消</button>
          </div>
        </div>
      </div>

      <p v-if="error" class="error">{{ error }}</p>
    </article>
  </section>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

import { api } from '../api'
import { authState } from '../stores/auth'

const router = useRouter()
const loading = ref(false)
const error = ref('')
const users = ref([])
const editForms = reactive({})

const filters = reactive({
  q: '',
  role: '',
})

const createForm = reactive({
  username: '',
  password: '',
  role: 'student',
  is_active: true,
})

const resetTargetId = ref(null)
const newPassword = ref('')
const showCreatePassword = ref(false)
const showResetPassword = ref(false)

const goAdminHome = () => router.push('/admin')
const isSelf = (item) => item.id === authState.user.id

const syncEditForms = () => {
  users.value.forEach((item) => {
    editForms[item.id] = {
      username: item.username,
      role: item.role,
      is_active: item.is_active,
    }
  })
}

const loadUsers = async () => {
  loading.value = true
  error.value = ''
  try {
    const res = await api.get('/admin/users/', {
      params: {
        q: filters.q || undefined,
        role: filters.role || undefined,
      },
    })
    users.value = res.data
    syncEditForms()
  } catch (err) {
    error.value = err?.response?.data?.error || '加载用户失败'
  } finally {
    loading.value = false
  }
}

const createUser = async () => {
  error.value = ''
  try {
    await api.post('/admin/users/', createForm)
    createForm.username = ''
    createForm.password = ''
    createForm.role = 'student'
    createForm.is_active = true
    await loadUsers()
  } catch (err) {
    error.value = err?.response?.data?.error || '创建用户失败'
  }
}

const updateUser = async (userId) => {
  error.value = ''
  if (userId === authState.user.id) {
    error.value = '当前管理员账号不允许自我修改'
    return
  }
  try {
    await api.put(`/admin/users/${userId}/`, editForms[userId])
    await loadUsers()
  } catch (err) {
    error.value = err?.response?.data?.error || '更新用户失败'
  }
}

const toggleUser = async (item) => {
  error.value = ''
  if (isSelf(item)) {
    error.value = '当前管理员账号不允许自我禁用'
    return
  }
  try {
    await api.put(`/admin/users/${item.id}/`, {
      is_active: !item.is_active,
    })
    await loadUsers()
  } catch (err) {
    error.value = err?.response?.data?.error || '切换用户状态失败'
  }
}

const removeUser = async (item) => {
  error.value = ''
  if (isSelf(item)) {
    error.value = '当前管理员账号不允许自我删除'
    return
  }
  if (!window.confirm(`确认删除用户 ${item.username}？`)) return
  try {
    await api.delete(`/admin/users/${item.id}/`)
    await loadUsers()
  } catch (err) {
    error.value = err?.response?.data?.error || '删除用户失败'
  }
}

const openReset = (id) => {
  if (id === authState.user.id) {
    error.value = '当前管理员账号不允许自我重置密码'
    return
  }
  resetTargetId.value = id
  newPassword.value = ''
  showResetPassword.value = false
}

const closeReset = () => {
  resetTargetId.value = null
  newPassword.value = ''
}

const resetPassword = async (id) => {
  error.value = ''
  if (id === authState.user.id) {
    error.value = '当前管理员账号不允许自我重置密码'
    return
  }
  try {
    await api.post(`/admin/users/${id}/reset-password/`, {
      new_password: newPassword.value,
    })
    closeReset()
  } catch (err) {
    error.value = err?.response?.data?.error || '重置密码失败'
  }
}

onMounted(loadUsers)
</script>

<style scoped>
.mini {
  width: 220px;
}

.mini-wrap {
  width: 220px;
}

.inline-check {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
}

.inline-check input {
  width: auto;
}

.error {
  color: var(--danger);
  font-weight: 700;
}

.danger-btn {
  border: 1px solid var(--danger-line);
  color: var(--danger);
  background: var(--danger-soft);
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
