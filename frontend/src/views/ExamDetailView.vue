<template>
  <section class="exam-focus-shell stack-lg">
    <header class="exam-sticky">
      <div>
        <h2>{{ exam.title || '考试中' }}</h2>
        <p class="tiny">{{ exam.description || '请专注作答，交卷后将返回学生首页。' }}</p>
      </div>

      <div class="exam-actions">
        <span v-if="exam.questions.length" class="tiny progress-text">第 {{ currentIndex + 1 }} / {{ exam.questions.length }} 题</span>
        <div v-if="showTimer" class="timer-pill" :class="{ danger: timeLeft <= 60 }">{{ timerText }}</div>
        <button class="ghost" @click="goBack">返回</button>
        <button
          v-if="!isTeacher && !exam.attempted && !submitted"
          class="primary"
          :disabled="submitting"
          @click="confirmAndSubmit"
        >
          {{ submitting ? '交卷中...' : '交卷' }}
        </button>
      </div>
    </header>

    <article v-if="loading" class="panel">
      <SkeletonBlock :rows="4" />
    </article>

    <article v-else class="exam-layout">
      <aside class="panel nav-panel stack-sm">
        <div class="row-between">
          <h4>题目导航</h4>
          <span class="tiny">已答 {{ answeredCount }} / {{ exam.questions.length }}</span>
        </div>

        <div class="question-grid">
          <button
            v-for="(q, idx) in exam.questions"
            :key="q.id"
            class="q-index"
            :class="{
              current: idx === currentIndex,
              answered: questionAnswered(q),
            }"
            type="button"
            @click="currentIndex = idx"
          >
            {{ idx + 1 }}
          </button>
        </div>
      </aside>

      <main class="panel question-panel stack">
        <template v-if="currentQuestion">
          <div class="row-between">
            <h3>第 {{ currentIndex + 1 }} 题</h3>
            <span class="pill pill-draft">{{ questionTypeLabel(currentQuestion.question_type) }} · {{ currentQuestion.score }}分</span>
          </div>

          <p class="question-text">{{ currentQuestion.text }}</p>

          <div v-if="isChoiceType(currentQuestion.question_type)" class="stack-sm">
            <button
              v-for="(opt, oIdx) in displayOptions(currentQuestion)"
              :key="`${currentQuestion.id}-${oIdx}`"
              class="choice-row"
              :class="{ selected: isOptionSelected(currentQuestion, oIdx) }"
              type="button"
              :disabled="isReadOnly"
              @click="selectOption(currentQuestion.id, oIdx)"
            >
              <span class="choice-mark">{{ isOptionSelected(currentQuestion, oIdx) ? '✓' : optionCode(oIdx) }}</span>
              <span>{{ opt }}</span>
            </button>
          </div>

          <textarea
            v-if="!isChoiceType(currentQuestion.question_type)"
            v-model="answers[currentQuestion.id]"
            rows="8"
            :disabled="isReadOnly"
            placeholder="请输入你的答案"
          ></textarea>

          <p v-if="isTeacher && (currentQuestion.question_type === 'single' || currentQuestion.question_type === 'judge')" class="tiny">
            标准答案：{{ letter(currentQuestion.correct_option) }}
          </p>
          <p v-if="isTeacher && currentQuestion.question_type === 'multiple'" class="tiny">
            标准答案：{{ optionSetLabel(currentQuestion.correct_options || []) }}
          </p>
          <p v-if="isTeacher && currentQuestion.question_type === 'short'" class="tiny">
            参考答案：{{ currentQuestion.reference_answer || '未设置' }}
          </p>

          <div class="row-between">
            <button class="ghost" :disabled="currentIndex === 0" @click="currentIndex -= 1">上一题</button>
            <button class="ghost" :disabled="currentIndex >= exam.questions.length - 1" @click="currentIndex += 1">下一题</button>
          </div>
        </template>
      </main>
    </article>

    <p v-if="exam.attempted && !result && !isTeacher" class="muted">你已提交该试卷，可在仪表盘查看成绩。</p>
    <p v-if="error" class="error">{{ error }}</p>
  </section>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { api } from '../api'
import SkeletonBlock from '../components/SkeletonBlock.vue'
import { authState } from '../stores/auth'

const route = useRoute()
const router = useRouter()
const examId = route.params.id

const loading = ref(false)
const submitting = ref(false)
const error = ref('')

const exam = reactive({
  title: '',
  description: '',
  duration_minutes: 0,
  questions: [],
  attempted: false,
})

const result = ref(null)
const answers = reactive({})
const timeLeft = ref(0)
let timerId = null
const currentIndex = ref(0)

const isTeacher = computed(() => authState.user.role === 'teacher')
const submitted = computed(() => Boolean(result.value))
const isReadOnly = computed(() => isTeacher.value || exam.attempted || submitted.value)
const currentQuestion = computed(() => exam.questions[currentIndex.value] || null)
const showTimer = computed(() => !isTeacher.value && !exam.attempted && !submitted.value && timeLeft.value > 0)
const answeredCount = computed(() => exam.questions.filter((q) => questionAnswered(q)).length)
const timerText = computed(() => {
  const m = String(Math.floor(timeLeft.value / 60)).padStart(2, '0')
  const s = String(timeLeft.value % 60).padStart(2, '0')
  return `剩余 ${m}:${s}`
})

const getTimerStorageKey = () => `exam_start_${authState.user.id}_${examId}`

const clearCountdown = () => {
  if (timerId) {
    clearInterval(timerId)
    timerId = null
  }
}

const startCountdown = () => {
  if (isTeacher.value || exam.attempted) {
    return
  }

  const key = getTimerStorageKey()
  let startTs = Number(localStorage.getItem(key))
  if (!startTs) {
    startTs = Date.now()
    localStorage.setItem(key, String(startTs))
  }

  const total = exam.duration_minutes * 60

  const tick = async () => {
    const elapsed = Math.floor((Date.now() - startTs) / 1000)
    const remain = Math.max(0, total - elapsed)
    timeLeft.value = remain

    if (remain <= 0) {
      clearCountdown()
      await submit(true)
    }
  }

  tick()
  timerId = setInterval(tick, 1000)
}

const loadExam = async () => {
  loading.value = true
  error.value = ''

  try {
    const response = await api.get(`/exams/${examId}/`)
    Object.assign(exam, response.data)
    currentIndex.value = 0
    exam.questions.forEach((q) => {
      if (q.question_type === 'multiple' && !Array.isArray(answers[q.id])) {
        answers[q.id] = []
      }
      if (q.question_type === 'short' && answers[q.id] === undefined) {
        answers[q.id] = ''
      }
    })
    startCountdown()
  } catch (err) {
    error.value = err?.response?.data?.error || '加载试卷失败'
  } finally {
    loading.value = false
  }
}

const isChoiceType = (questionType) => ['single', 'multiple', 'judge'].includes(questionType)

const questionAnswered = (question) => {
  const answer = answers[question.id]
  if (question.question_type === 'multiple') {
    return Array.isArray(answer) && answer.length > 0
  }
  if (question.question_type === 'short') {
    return String(answer || '').trim().length > 0
  }
  return answer !== null && answer !== undefined && String(answer) !== ''
}

const displayOptions = (question) => {
  const opts = Array.isArray(question.options) ? question.options : []
  if (question.question_type === 'judge') {
    return opts.filter((x) => String(x || '').trim() !== '').slice(0, 2)
  }
  return opts
}

const questionTypeLabel = (questionType) => {
  const map = {
    single: '单选题',
    multiple: '多选题',
    judge: '判断题',
    short: '简答题',
    subjective: '简答题',
  }
  return map[questionType] || questionType
}

const isOptionSelected = (question, optionIndex) => {
  if (question.question_type === 'multiple') {
    return Array.isArray(answers[question.id]) && answers[question.id].includes(optionIndex)
  }
  return Number(answers[question.id]) === optionIndex
}

const selectOption = (questionId, optionIndex) => {
  const question = exam.questions.find((q) => q.id === questionId)
  if (!question) return

  if (question.question_type === 'multiple') {
    const current = Array.isArray(answers[questionId]) ? [...answers[questionId]] : []
    const idx = current.indexOf(optionIndex)
    if (idx >= 0) current.splice(idx, 1)
    else current.push(optionIndex)
    answers[questionId] = current
    return
  }

  answers[questionId] = optionIndex
}

const optionSetLabel = (values) => {
  const arr = Array.isArray(values) ? values : []
  if (!arr.length) return '未设置'
  return arr.map((v) => letter(v)).join('、')
}

const confirmAndSubmit = async () => {
  if (submitting.value || isTeacher.value || exam.attempted || submitted.value) return
  const ok = window.confirm('确认提交试卷吗？提交后将直接返回学生首页。')
  if (!ok) return
  await submit(false)
}

const goBack = () => {
  if (window.history.length > 1) {
    router.back()
    return
  }
  if (isTeacher.value) {
    router.push('/teacher')
    return
  }
  router.push('/dashboard')
}

const submit = async (autoSubmit = false) => {
  if (submitting.value || isTeacher.value || exam.attempted || submitted.value) {
    return
  }

  submitting.value = true
  error.value = ''

  try {
    const payloadAnswers = {}
    exam.questions.forEach((q) => {
      const val = answers[q.id]
      if (q.question_type === 'multiple') {
        payloadAnswers[q.id] = Array.isArray(val) ? val : []
      } else {
        payloadAnswers[q.id] = val
      }
    })

    const response = await api.post(`/exams/${examId}/submit/`, {
      answers: payloadAnswers,
    })
    result.value = response.data
    exam.attempted = true
    localStorage.removeItem(getTimerStorageKey())
    clearCountdown()

    if (autoSubmit) {
      error.value = '时间到，系统已自动交卷。'
    }

    if (!isTeacher.value) {
      router.push('/dashboard')
    }
  } catch (err) {
    error.value = err?.response?.data?.error || '提交失败'
  } finally {
    submitting.value = false
  }
}

const optionCode = (index) => {
  if (Number.isNaN(index) || index < 0) return String(index)
  const alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
  if (index < alphabet.length) return alphabet[index]
  const head = Math.floor(index / alphabet.length) - 1
  const tail = index % alphabet.length
  return `${alphabet[Math.max(0, head)]}${alphabet[tail]}`
}

const letter = (idx) => optionCode(Number(idx))

onMounted(loadExam)
onBeforeUnmount(clearCountdown)
</script>

<style scoped>
.exam-focus-shell {
  padding: 1rem;
}

.exam-sticky {
  position: sticky;
  top: 0;
  z-index: 8;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
  padding: 0.9rem 1rem;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(8px);
  box-shadow: var(--shadow-sm);
}

.exam-actions {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.progress-text {
  min-width: 86px;
  text-align: right;
}

.exam-layout {
  display: grid;
  grid-template-columns: 260px minmax(0, 1fr);
  gap: 1rem;
  align-items: start;
}

.nav-panel {
  position: sticky;
  top: 84px;
}

.question-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 0.5rem;
}

.q-index {
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  height: 38px;
  font-weight: 700;
  background: #fff;
}

.q-index.answered {
  border-color: #34d399;
  background: #ecfdf5;
  color: #047857;
}

.q-index.current {
  border-color: #2563eb;
  background: #dbeafe;
  color: #1d4ed8;
}

.question-panel {
  min-height: 520px;
}

.question-text {
  font-size: 1.06rem;
  line-height: 1.7;
  white-space: pre-wrap;
}

.choice-row {
  display: flex;
  align-items: center;
  gap: 0.7rem;
  width: 100%;
  text-align: left;
  cursor: pointer;
  color: var(--ink);
  background: #fff;
  border: 1px solid #dbe3f0;
  border-radius: 12px;
  padding: 0.82rem 0.95rem;
}

.choice-mark {
  width: 24px;
  height: 24px;
  display: inline-grid;
  place-items: center;
  border-radius: 999px;
  border: 1px solid #bfdbfe;
  color: var(--brand);
  font-size: 0.85rem;
  font-weight: 800;
  background: #eff6ff;
}

.choice-row:not(.selected):hover:not(:disabled) {
  border-color: #3b82f6;
  background: #eff6ff;
}

.choice-row.selected {
  border-color: #2563eb;
  background: #eff6ff;
  color: #1e3a8a;
  box-shadow: 0 0 0 1px rgba(37, 99, 235, 0.2);
  font-weight: 700;
}

.choice-row.selected .choice-mark {
  border-color: #2563eb;
  background: #2563eb;
  color: #fff;
}

.choice-row.selected:hover:not(:disabled) {
  border-color: #1d4ed8;
  background: #dbeafe;
  color: #1e3a8a;
}

.choice-row:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.timer-pill {
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  color: #1e40af;
  border-radius: 999px;
  padding: 0.38rem 0.75rem;
  font-weight: 700;
}

.timer-pill.danger {
  background: #fef2f2;
  border-color: #fecaca;
  color: var(--danger);
  animation: pulse-alert 1s infinite;
}

.error {
  color: var(--danger);
  font-weight: 700;
}

@media (max-width: 900px) {
  .exam-layout {
    grid-template-columns: 1fr;
  }

  .nav-panel {
    position: static;
  }

  .exam-sticky {
    flex-direction: column;
    align-items: flex-start;
  }

  .exam-actions {
    width: 100%;
    justify-content: flex-start;
  }
}
</style>
