<template>
  <section class="stack-lg">
    <article class="panel row-between">
      <div>
        <h2>{{ exam.title }}</h2>
        <p class="muted">{{ exam.description || '暂无描述' }}</p>
        <p class="tiny">考试时长：{{ exam.duration_minutes }} 分钟 · 题目数：{{ exam.questions?.length || 0 }}</p>
      </div>
      <div class="row-wrap">
        <BackButton />
        <div v-if="showTimer" class="timer-pill" :class="{ danger: timeLeft <= 60 }">
          倒计时：{{ timerText }}
        </div>
      </div>
    </article>

    <article class="panel stack" v-if="loading">加载中...</article>

    <article v-else class="panel stack">
      <div v-for="(q, idx) in exam.questions" :key="q.id" class="card stack-sm">
        <h4>{{ idx + 1 }}. {{ q.text }} <span class="tiny">（{{ questionTypeLabel(q.question_type) }}）</span></h4>

        <template v-if="isChoiceType(q.question_type)">
          <button
            v-for="(opt, oIdx) in displayOptions(q)"
            :key="oIdx"
            class="choice-row"
            :class="{ selected: isOptionSelected(q, oIdx) }"
            type="button"
            :disabled="isTeacher || exam.attempted || submitted"
            @click="selectOption(q.id, oIdx)"
          >
            {{ String.fromCharCode(65 + oIdx) }}. {{ opt }}
          </button>
        </template>

        <template v-else-if="q.question_type === 'blank'">
          <input
            v-model="answers[q.id]"
            :disabled="isTeacher || exam.attempted || submitted"
            type="text"
            placeholder="请输入填空答案"
          />
        </template>

        <template v-else>
          <textarea
            v-model="answers[q.id]"
            rows="3"
            :disabled="isTeacher || exam.attempted || submitted"
            placeholder="请输入主观题答案"
          ></textarea>
        </template>

        <p v-if="isTeacher && (q.question_type === 'single' || q.question_type === 'judge')" class="tiny">
          答案：{{ letter(q.correct_option) }} · 分值：{{ q.score }}
        </p>
        <p v-if="isTeacher && q.question_type === 'multiple'" class="tiny">
          答案：{{ optionSetLabel(q.correct_options || []) }} · 分值：{{ q.score }}
        </p>
        <p v-if="isTeacher && (q.question_type === 'blank' || q.question_type === 'short')" class="tiny">
          参考答案：{{ q.reference_answer || '未设置' }} · 关键词：{{ q.keyword_answers || '未设置' }} · 分值：{{ q.score }}
        </p>
      </div>

      <button
        v-if="!isTeacher && !exam.attempted && !submitted"
        class="primary"
        :disabled="submitting"
        @click="confirmAndSubmit"
      >
        {{ submitting ? '提交中...' : '提交试卷' }}
      </button>

      <p v-if="exam.attempted && !result && !isTeacher" class="muted">你已提交该试卷，可在仪表盘查看成绩。</p>
      <p v-if="error" class="error">{{ error }}</p>
    </article>
  </section>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { api } from '../api'
import BackButton from '../components/BackButton.vue'
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

const isTeacher = computed(() => authState.user.role === 'teacher')
const submitted = computed(() => Boolean(result.value))
const showTimer = computed(() => !isTeacher.value && !exam.attempted && !submitted.value && timeLeft.value > 0)
const timerText = computed(() => {
  const m = String(Math.floor(timeLeft.value / 60)).padStart(2, '0')
  const s = String(timeLeft.value % 60).padStart(2, '0')
  return `${m}:${s}`
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
    exam.questions.forEach((q) => {
      if (q.question_type === 'multiple' && !Array.isArray(answers[q.id])) {
        answers[q.id] = []
      }
      if ((q.question_type === 'blank' || q.question_type === 'short') && answers[q.id] === undefined) {
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
    blank: '填空题',
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

const letter = (idx) => String.fromCharCode(65 + idx)

onMounted(loadExam)
onBeforeUnmount(clearCountdown)
</script>

<style scoped>
.choice-row {
  display: block;
  width: 100%;
  text-align: left;
  cursor: pointer;
  color: inherit;
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 0.6rem 0.75rem;
}

.choice-row:hover:not(:disabled) {
  border-color: #3f8f68;
  background: #eef9f3;
}

.choice-row.selected {
  border-color: #146b43;
  background: #1f8b5f;
  color: #fff;
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.25);
  font-weight: 700;
}

.choice-row:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.score-result {
  border: 1px solid var(--ok-line);
  background: var(--ok-soft);
  border-radius: 14px;
  padding: 0.9rem 1rem;
}

.timer-pill {
  background: #f3fbf7;
  border: 1px solid #cfe6da;
  color: var(--brand-deep);
  border-radius: 999px;
  padding: 0.38rem 0.75rem;
  font-weight: 700;
}

.timer-pill.danger {
  background: #fff2f2;
  border-color: #f3c8c8;
  color: var(--danger);
}

.error {
  color: var(--danger);
  font-weight: 700;
}
</style>
