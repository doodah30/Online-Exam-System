<template>
  <section class="stack-lg">
    <article class="panel row-between">
      <div>
        <h2>操作日志</h2>
        <p class="muted">审计系统关键行为，支持按动作与关键词过滤。</p>
      </div>
      <button class="ghost" @click="goAdminHome">返回管理员控制台</button>
    </article>

    <article class="panel stack">
      <div class="row-wrap">
        <input class="mini" v-model.trim="filters.action" placeholder="动作，例如 user_login" />
        <input class="mini" v-model.trim="filters.q" placeholder="关键词（用户/详情）" />
        <input class="mini" v-model.number="filters.limit" type="number" min="1" max="500" />
        <button class="ghost" @click="loadLogs">查询</button>
      </div>

      <p v-if="loading" class="muted">加载中...</p>
      <p v-else-if="logs.length === 0" class="muted">暂无日志</p>

      <div v-else class="stack-sm">
        <div v-for="item in logs" :key="item.id" class="card stack-sm">
          <div class="row-between">
            <strong>{{ item.action }}</strong>
            <span class="tiny">{{ formatDate(item.created_at) }}</span>
          </div>
          <p class="tiny">操作者：{{ item.actor_username || 'anonymous' }} · IP：{{ item.ip_address || '-' }}</p>
          <p class="tiny">目标：{{ item.target_type || '-' }} #{{ item.target_id || '-' }} {{ item.target_label || '' }}</p>
          <p class="tiny">详情：{{ item.detail || '-' }}</p>
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

const router = useRouter()
const loading = ref(false)
const error = ref('')
const logs = ref([])

const filters = reactive({
  action: '',
  q: '',
  limit: 100,
})

const goAdminHome = () => router.push('/admin')

const loadLogs = async () => {
  loading.value = true
  error.value = ''
  try {
    const res = await api.get('/admin/logs/', {
      params: {
        action: filters.action || undefined,
        q: filters.q || undefined,
        limit: filters.limit || 100,
      },
    })
    logs.value = res.data
  } catch (err) {
    error.value = err?.response?.data?.error || '加载日志失败'
  } finally {
    loading.value = false
  }
}

const formatDate = (dateText) => new Date(dateText).toLocaleString()

onMounted(loadLogs)
</script>

<style scoped>
.mini {
  width: 220px;
}

.error {
  color: var(--danger);
  font-weight: 700;
}
</style>
