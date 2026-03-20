<template>
  <section class="stack-lg">
    <article class="panel row-between">
      <div>
        <h2>课程统计图表（样例）</h2>
        <p class="muted">课程：{{ course.name || '加载中...' }}</p>
      </div>
      <div class="row-wrap">
        <BackButton />
        <button class="ghost" @click="loadStats">刷新</button>
      </div>
    </article>

    <article class="panel stack">
      <h3>按试卷统计（平均分）</h3>
      <p v-if="loading" class="muted">加载中...</p>
      <p v-else-if="examStats.length === 0" class="muted">该课程暂时没有试卷</p>

      <div v-else class="stack-sm">
        <div v-for="row in examStats" :key="row.exam_id" class="bar-row">
          <div class="bar-title">{{ row.exam_title }}（{{ row.submission_count }}人）</div>
          <div class="bar-bg">
            <div class="bar-fill" :style="{ width: `${Math.min(100, row.avg_score)}%` }"></div>
          </div>
          <div class="bar-num">{{ row.avg_score }}</div>
        </div>
      </div>
    </article>

    <article class="panel stack">
      <h3>按学生统计（平均分）</h3>
      <p v-if="studentStats.length === 0" class="muted">暂无学生数据</p>

      <div v-else class="stack-sm">
        <div v-for="row in studentStats" :key="row.student_id" class="bar-row">
          <div class="bar-title">{{ row.student_username }}（{{ row.submission_count }}次）</div>
          <div class="bar-bg">
            <div class="bar-fill warm" :style="{ width: `${Math.min(100, row.avg_score)}%` }"></div>
          </div>
          <div class="bar-num">{{ row.avg_score }}</div>
        </div>
      </div>

      <p v-if="error" class="error">{{ error }}</p>
    </article>
  </section>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'

import BackButton from '../components/BackButton.vue'
import { api } from '../api'

const route = useRoute()
const courseId = route.params.id

const loading = ref(false)
const error = ref('')
const course = reactive({ id: null, name: '' })
const examStats = ref([])
const studentStats = ref([])

const loadStats = async () => {
  loading.value = true
  error.value = ''

  try {
    const res = await api.get(`/courses/${courseId}/stats/`)
    Object.assign(course, res.data.course)
    examStats.value = res.data.exam_stats
    studentStats.value = res.data.student_stats
  } catch (err) {
    error.value = err?.response?.data?.error || '加载统计失败'
  } finally {
    loading.value = false
  }
}

onMounted(loadStats)
</script>

<style scoped>
.bar-row {
  display: grid;
  grid-template-columns: 1.6fr 3fr auto;
  align-items: center;
  gap: 0.7rem;
}

.bar-bg {
  height: 14px;
  border-radius: 999px;
  background: #e8f1e8;
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  border-radius: 999px;
  background: linear-gradient(90deg, var(--brand), #3bb78f);
}

.bar-fill.warm {
  background: linear-gradient(90deg, #f0a202, #f18805);
}

.bar-title {
  font-weight: 600;
}

.bar-num {
  font-weight: 700;
  color: var(--brand-deep);
}

.error {
  color: var(--danger);
  font-weight: 700;
}

@media (max-width: 720px) {
  .bar-row {
    grid-template-columns: 1fr;
  }
}
</style>
