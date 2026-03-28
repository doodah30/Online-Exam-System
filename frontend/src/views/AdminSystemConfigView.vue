<template>
  <section class="stack-lg">
    <article class="panel row-between">
      <div>
        <h2>系统配置</h2>
        <p class="muted">维护系统基础运行参数。</p>
      </div>
      <button class="ghost" @click="goAdminHome">返回管理员控制台</button>
    </article>

    <article class="panel stack">
      <h3>运行参数</h3>
      <div class="grid two-col">
        <label>
          自动保存间隔（秒）
          <input v-model.number="form.auto_save_interval_seconds" type="number" min="5" />
        </label>
        <label>
          考试并发上限
          <input v-model.number="form.max_exam_concurrency" type="number" min="1" />
        </label>
      </div>

      <div class="row-wrap">
        <button class="ghost" @click="loadConfig">刷新</button>
        <button class="primary" @click="saveConfig">保存配置</button>
      </div>

      <p class="tiny">最后更新：{{ form.updated_at ? formatDate(form.updated_at) : '-' }} · 更新人：{{ form.updated_by || '-' }}</p>
      <p v-if="error" class="error">{{ error }}</p>
    </article>
  </section>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

import { api } from '../api'

const router = useRouter()
const error = ref('')

const form = reactive({
  id: null,
  auto_save_interval_seconds: 30,
  max_exam_concurrency: 200,
  updated_by: '',
  updated_at: '',
})

const goAdminHome = () => router.push('/admin')

const loadConfig = async () => {
  error.value = ''
  try {
    const res = await api.get('/admin/system-config/')
    Object.assign(form, res.data)
  } catch (err) {
    error.value = err?.response?.data?.error || '加载配置失败'
  }
}

const saveConfig = async () => {
  error.value = ''
  try {
    const res = await api.put('/admin/system-config/', {
      auto_save_interval_seconds: form.auto_save_interval_seconds,
      max_exam_concurrency: form.max_exam_concurrency,
    })
    Object.assign(form, res.data)
  } catch (err) {
    error.value = err?.response?.data?.error || '保存配置失败'
  }
}

const formatDate = (dateText) => new Date(dateText).toLocaleString()

onMounted(loadConfig)
</script>

<style scoped>
.error {
  color: var(--danger);
  font-weight: 700;
}
</style>
