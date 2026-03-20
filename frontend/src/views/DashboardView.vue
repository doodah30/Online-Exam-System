<template>
  <section class="stack-lg">
    <article class="panel">
      <h2>学生控制台</h2>
      <p class="muted">欢迎你，{{ auth.user.username }}。请选择要进入的功能。</p>
    </article>

    <article class="panel stack">
      <div class="grid two-col">
        <div class="card portal-card">
          <h3>参加考试</h3>
          <p class="muted">查看所有可参加的试卷并进入作答。</p>
          <button class="primary" @click="goStudentExams">进入参加考试</button>
        </div>

        <div class="card portal-card">
          <h3>我的成绩</h3>
          <p class="muted">查看已发布成绩与提交记录。</p>
          <button class="primary" @click="goStudentScores">进入我的成绩</button>
        </div>
      </div>
    </article>

    <p v-if="error" class="error">{{ error }}</p>
  </section>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { authState } from '../stores/auth'

const auth = authState
const router = useRouter()
const error = ref('')

const goStudentExams = () => {
  router.push('/student/exams')
}

const goStudentScores = () => {
  router.push('/student/scores')
}

onMounted(() => {
  if (auth.user.role === 'teacher') {
    router.replace('/teacher')
    return
  }
})
</script>

<style scoped>
.portal-card {
  display: grid;
  gap: 0.75rem;
  align-content: start;
  min-height: 160px;
}

.error {
  color: var(--danger);
  font-weight: 700;
}
</style>
