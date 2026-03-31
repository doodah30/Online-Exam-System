<template>
  <section class="stack-lg">
    <article class="panel row-between">
      <div>
        <h2>参加考试</h2>
        <p class="muted">查看可参加试卷并进入作答。</p>
      </div>
      <button class="ghost" @click="goBack">返回学生控制台</button>
    </article>

    <article class="panel stack">
      <div class="row-between">
        <h3>可参加考试</h3>
        <button class="ghost" @click="loadExams">刷新</button>
      </div>

      <p v-if="loading" class="muted">加载中...</p>
      <p v-else-if="pendingExams.length === 0" class="muted">暂无可参加考试</p>

      <div v-else class="stack-sm">
        <div v-for="exam in pendingExams" :key="exam.id" class="card exam-row">
          <div>
            <h4>{{ exam.title }}</h4>
            <p class="muted">{{ exam.description || '暂无描述' }}</p>
            <p class="tiny">
              题目数：{{ exam.question_count }} · 时长：{{ exam.duration_minutes }} 分钟
              <span v-if="exam.course"> · 课程：{{ exam.course.name }}</span>
            </p>
          </div>

          <div class="row-wrap">
            <button class="ghost" @click="goExam(exam.id)">进入考试</button>
          </div>
        </div>
      </div>
    </article>

    <article class="panel stack">
      <div class="row-between">
        <h3>已完成考试</h3>
        <span class="tiny muted">已提交的考试可查看答卷</span>
      </div>

      <p v-if="loading" class="muted">加载中...</p>
      <p v-else-if="completedExams.length === 0" class="muted">暂无已完成考试</p>

      <div v-else class="stack-sm">
        <div v-for="exam in completedExams" :key="`done-${exam.id}`" class="card exam-row done-row">
          <div>
            <h4>{{ exam.title }}</h4>
            <p class="muted">{{ exam.description || '暂无描述' }}</p>
            <p class="tiny">
              题目数：{{ exam.question_count }} · 时长：{{ exam.duration_minutes }} 分钟
              <span v-if="exam.course"> · 课程：{{ exam.course.name }}</span>
            </p>
          </div>

          <div class="row-wrap">
            <button class="ghost" @click="goReview(exam.id)">查看答卷</button>
            <span class="tag-done">已作答</span>
          </div>
        </div>
      </div>
    </article>

    <p v-if="error" class="error">{{ error }}</p>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { api } from '../api'
import { authState } from '../stores/auth'

const router = useRouter()
const exams = ref([])
const mySubmissions = ref([])
const loading = ref(false)
const error = ref('')

const pendingExams = computed(() => exams.value.filter((x) => !x.attempted))
const completedExams = computed(() => exams.value.filter((x) => x.attempted))

const loadExams = async () => {
  loading.value = true
  error.value = ''
  try {
    const [examRes, subRes] = await Promise.all([
      api.get('/exams/'),
      api.get('/submissions/mine/'),
    ])
    exams.value = examRes.data
    mySubmissions.value = subRes.data
  } catch (err) {
    error.value = err?.response?.data?.error || '加载试卷失败'
  } finally {
    loading.value = false
  }
}

const goExam = (id) => {
  router.push(`/exams/${id}`)
}

const goReview = (examId) => {
  const hit = mySubmissions.value.find((x) => x.exam_id === examId)
  if (!hit) {
    error.value = '未找到该试卷的答卷记录'
    return
  }
  router.push(`/submissions/${hit.submission_id}/review`)
}

const goBack = () => {
  router.push('/dashboard')
}

onMounted(async () => {
  if (authState.user.role === 'teacher') {
    router.replace('/teacher')
    return
  }
  await loadExams()
})
</script>

<style scoped>
.tag-done {
  padding: 0.3rem 0.55rem;
  border-radius: 999px;
  background: var(--ok-soft);
  color: var(--ok);
  border: 1px solid var(--ok-line);
  font-size: 0.8rem;
  font-weight: 700;
}

.error {
  color: var(--danger);
  font-weight: 700;
}

.done-row {
  border: 1px solid #b8dccb;
  background: #f5fcf8;
}
</style>
