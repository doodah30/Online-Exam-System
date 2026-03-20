<template>
  <section class="stack-lg">
    <article class="panel row-between">
      <div>
        <h2>阅卷中心</h2>
        <p class="muted">{{ exam.title || '加载中...' }}</p>
      </div>
      <div class="row-wrap">
        <button class="ghost" @click="goBack">返回上一页</button>
        <button class="ghost" @click="loadOverview">刷新</button>
        <button class="primary" @click="releaseResults">发布已阅成绩</button>
      </div>
    </article>

    <article class="panel stack">
      <h3>未提交学生</h3>
      <p v-if="missingStudents.length === 0" class="muted">当前全部已提交，或该试卷不绑定课程。</p>
      <div v-else class="row-wrap">
        <span v-for="stu in missingStudents" :key="stu.student_id" class="tag">{{ stu.student_username }}</span>
      </div>
    </article>

    <article class="panel stack">
      <h3>逐份阅卷</h3>
      <p v-if="loading" class="muted">加载中...</p>
      <p v-else-if="submissions.length === 0" class="muted">暂无提交记录</p>

      <template v-else>
        <div class="row-between">
          <button class="ghost" :disabled="currentIndex <= 0" @click="goPrev">上一份</button>
          <p class="tiny">第 {{ currentIndex + 1 }} / {{ submissions.length }} 份</p>
          <button class="ghost" :disabled="currentIndex >= submissions.length - 1" @click="goNext">下一份</button>
        </div>

        <div class="card stack-sm">
          <div class="row-between">
            <h4>{{ current.student_username }}</h4>
            <div class="row-wrap">
              <span class="tiny">{{ current.status === 'graded' ? '已阅' : '待阅' }}</span>
              <span class="tiny">{{ current.is_result_published ? '已发布' : '未发布' }}</span>
              <strong>{{ current.total_score }} / {{ current.max_score }}</strong>
            </div>
          </div>
          <p class="tiny">提交时间：{{ formatDate(current.submitted_at) }}</p>

          <div class="stack-sm" v-if="current.answers?.length">
            <div v-for="ans in current.answers" :key="`${current.submission_id}-${ans.question_id}`" class="answer-row">
              <p class="tiny">第{{ ans.question_no }}题 [{{ ans.question_type === 'single' ? '单选' : '主观' }}]</p>
              <template v-if="ans.question_type === 'single'">
                <p class="tiny">学生作答：{{ optionLabel(ans.selected_option) }}</p>
                <p class="tiny">标准答案：{{ optionLabel(ans.correct_option) }}</p>
                <p class="tiny">得分：{{ ans.score_awarded }} / {{ ans.full_score }}</p>
              </template>
              <template v-else>
                <p class="tiny">学生答案：{{ ans.subjective_answer || '空' }}</p>
                <p class="tiny">标准答案：{{ ans.reference_answer || '未填写' }}</p>
                <div class="row-wrap">
                  <label class="tiny">评分：</label>
                  <input
                    class="mini-input"
                    type="number"
                    min="0"
                    :max="ans.full_score"
                    v-model.number="manualScores[current.submission_id][ans.question_id]"
                    @input="dirty = true"
                  />
                  <span class="tiny">/ {{ ans.full_score }}</span>
                </div>
              </template>
            </div>
          </div>

          <div class="row-wrap">
            <button class="primary" @click="saveCurrent">保存当前阅卷</button>
            <span class="tiny" v-if="dirty">当前有未保存更改</span>
          </div>
        </div>
      </template>

      <p v-if="error" class="error">{{ error }}</p>
    </article>
  </section>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { api } from '../api'

const route = useRoute()
const router = useRouter()
const examId = route.params.id

const loading = ref(false)
const error = ref('')
const dirty = ref(false)

const exam = reactive({ id: null, title: '' })
const submissions = ref([])
const missingStudents = ref([])
const manualScores = reactive({})
const currentIndex = ref(0)

const current = computed(() => submissions.value[currentIndex.value] || null)

const goBack = () => {
  if (window.history.length > 1) {
    router.back()
    return
  }
  router.push('/exam-management')
}

const initManualScores = () => {
  submissions.value.forEach((item) => {
    manualScores[item.submission_id] = manualScores[item.submission_id] || {}
    ;(item.answers || []).forEach((ans) => {
      if (ans.question_type === 'subjective') {
        manualScores[item.submission_id][ans.question_id] = ans.score_awarded
      }
    })
  })
}

const loadOverview = async () => {
  loading.value = true
  error.value = ''
  try {
    const [overviewRes, detailRes] = await Promise.all([
      api.get(`/exams/${examId}/grading/`),
      api.get(`/exams/${examId}/submissions/`),
    ])

    Object.assign(exam, overviewRes.data.exam)
    missingStudents.value = overviewRes.data.missing_students || []

    const answerMap = new Map(detailRes.data.submissions.map((x) => [x.submission_id, x.answers]))
    submissions.value = overviewRes.data.submissions.map((item) => ({
      ...item,
      answers: answerMap.get(item.submission_id) || [],
    }))

    initManualScores()
    if (currentIndex.value >= submissions.value.length) currentIndex.value = 0
    dirty.value = false
  } catch (err) {
    error.value = err?.response?.data?.error || '加载阅卷数据失败'
  } finally {
    loading.value = false
  }
}

const saveCurrent = async () => {
  if (!current.value) return
  error.value = ''
  try {
    await api.post(`/submissions/${current.value.submission_id}/grade/`, {
      subjective_scores: manualScores[current.value.submission_id] || {},
    })
    await loadOverview()
    dirty.value = false
  } catch (err) {
    error.value = err?.response?.data?.error || '保存阅卷失败'
  }
}

const guardNavigate = () => {
  if (!dirty.value) return true
  error.value = '请先保存当前阅卷后再切换到下一份/上一份。'
  return false
}

const goPrev = () => {
  if (!guardNavigate()) return
  currentIndex.value = Math.max(0, currentIndex.value - 1)
}

const goNext = () => {
  if (!guardNavigate()) return
  currentIndex.value = Math.min(submissions.value.length - 1, currentIndex.value + 1)
}

const releaseResults = async () => {
  error.value = ''
  try {
    await api.post(`/exams/${examId}/release-results/`)
    await loadOverview()
  } catch (err) {
    error.value = err?.response?.data?.error || '发布成绩失败'
  }
}

const optionLabel = (value) => {
  if (value === null || value === undefined || value === '') return '未作答'
  const index = Number(value)
  if (Number.isNaN(index) || index < 0 || index > 3) return String(value)
  return ['A', 'B', 'C', 'D'][index]
}

const formatDate = (dateText) => new Date(dateText).toLocaleString()

onMounted(loadOverview)
</script>

<style scoped>
.error {
  color: var(--danger);
  font-weight: 700;
}

.tag {
  border: 1px solid var(--line);
  border-radius: 999px;
  padding: 0.2rem 0.55rem;
}

.answer-row {
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 0.45rem 0.6rem;
}

.mini-input {
  width: 90px;
}
</style>
