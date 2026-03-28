<template>
  <section class="stack-lg">
    <article class="panel row-between">
      <div>
        <h2>考试全局管控</h2>
        <p class="muted">对考试执行暂停、恢复、强制结束。</p>
      </div>
      <button class="ghost" @click="goAdminHome">返回管理员控制台</button>
    </article>

    <article class="panel stack">
      <div class="row-between">
        <h3>考试列表</h3>
        <button class="ghost" @click="loadExams">刷新</button>
      </div>

      <p v-if="loading" class="muted">加载中...</p>
      <p v-else-if="exams.length === 0" class="muted">暂无考试</p>

      <div v-else class="stack-sm">
        <div v-for="exam in exams" :key="exam.id" class="card exam-row">
          <div>
            <h4>{{ exam.title }}</h4>
            <p class="tiny">创建者：{{ exam.created_by }} · 状态：{{ statusText(exam.control_status) }}</p>
            <p class="tiny">时长：{{ exam.duration_minutes }} 分钟 · 题目数：{{ exam.question_count }}</p>
          </div>

          <div class="row-wrap">
            <button class="ghost" @click="controlExam(exam.id, 'pause')">暂停</button>
            <button class="ghost" @click="controlExam(exam.id, 'resume')">恢复</button>
            <button class="danger-btn" @click="controlExam(exam.id, 'end')">强制结束</button>
          </div>
        </div>
      </div>

      <p v-if="error" class="error">{{ error }}</p>
    </article>
  </section>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { api } from '../api'

const router = useRouter()
const loading = ref(false)
const error = ref('')
const exams = ref([])

const goAdminHome = () => router.push('/admin')

const loadExams = async () => {
  loading.value = true
  error.value = ''
  try {
    const res = await api.get('/exams/')
    exams.value = res.data
  } catch (err) {
    error.value = err?.response?.data?.error || '加载考试失败'
  } finally {
    loading.value = false
  }
}

const controlExam = async (examId, action) => {
  error.value = ''
  try {
    await api.post(`/admin/exams/${examId}/control/`, { action })
    await loadExams()
  } catch (err) {
    error.value = err?.response?.data?.error || '操作失败'
  }
}

const statusText = (status) => {
  if (status === 'paused') return '已暂停'
  if (status === 'ended') return '已结束'
  return '进行中'
}

onMounted(loadExams)
</script>

<style scoped>
.error {
  color: var(--danger);
  font-weight: 700;
}

.danger-btn {
  border: 1px solid var(--danger-line);
  color: var(--danger);
  background: var(--danger-soft);
}
</style>
