<template>
  <section class="stack-lg">
    <article class="panel row-between">
      <div>
        <h2>我的成绩</h2>
        <p class="muted">查看提交记录和老师已发布成绩。</p>
      </div>
      <button class="ghost" @click="goBack">返回学生控制台</button>
    </article>

    <article class="panel stack">
      <div class="row-between">
        <h3>成绩列表</h3>
        <button class="ghost" @click="loadResults">刷新</button>
      </div>

      <p v-if="loading" class="muted">加载中...</p>
      <p v-else-if="results.length === 0" class="muted">还没有成绩记录</p>

      <div v-else class="stack-sm">
        <div v-for="item in results" :key="item.submission_id" class="card exam-row">
          <div>
            <h4>{{ item.exam_title }}</h4>
            <p class="tiny">提交时间：{{ formatDate(item.submitted_at) }}</p>
            <p class="tiny" v-if="item.course_name">课程：{{ item.course_name }}</p>
            <p class="tiny" v-if="!item.is_result_published">状态：已提交，待老师发布成绩</p>
          </div>
          <div class="score-pill">{{ item.is_result_published ? `${item.total_score} / ${item.max_score}` : '-- / --' }}</div>
        </div>
      </div>
    </article>

    <p v-if="error" class="error">{{ error }}</p>
  </section>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { api } from '../api'
import { authState } from '../stores/auth'

const router = useRouter()
const results = ref([])
const loading = ref(false)
const error = ref('')

const loadResults = async () => {
  loading.value = true
  error.value = ''
  try {
    const response = await api.get('/submissions/mine/')
    results.value = response.data
  } catch (err) {
    error.value = err?.response?.data?.error || '加载成绩失败'
  } finally {
    loading.value = false
  }
}

const goBack = () => {
  router.push('/dashboard')
}

const formatDate = (dateText) => new Date(dateText).toLocaleString()

onMounted(async () => {
  if (authState.user.role === 'teacher') {
    router.replace('/teacher')
    return
  }
  await loadResults()
})
</script>

<style scoped>
.score-pill {
  font-size: 1.1rem;
  font-weight: 800;
  color: var(--brand-deep);
}

.error {
  color: var(--danger);
  font-weight: 700;
}
</style>
