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
        <h4>{{ idx + 1 }}. {{ q.text }} <span class="tiny">（{{ q.question_type === 'single' ? '单选题' : '主观题' }}）</span></h4>

        <template v-if="q.question_type === 'single'">
          <label v-for="(opt, oIdx) in q.options" :key="oIdx" class="choice-row">
            <span>{{ String.fromCharCode(65 + oIdx) }}. {{ opt }}</span>
            <input
              :disabled="isTeacher || exam.attempted || submitted"
              type="radio"
              :name="`q_${q.id}`"
              :value="oIdx"
              v-model.number="answers[q.id]"
            />
          </label>
        </template>

        <template v-else>
          <textarea
            v-model="answers[q.id]"
            rows="3"
            :disabled="isTeacher || exam.attempted || submitted"
            placeholder="请输入主观题答案"
          ></textarea>
        </template>

        <p v-if="isTeacher && q.question_type === 'single'" class="tiny">答案：{{ letter(q.correct_option) }} · 分值：{{ q.score }}</p>
        <p v-if="isTeacher && q.question_type === 'subjective'" class="tiny">
          参考答案：{{ q.reference_answer || '未设置' }} · 关键词：{{ q.keyword_answers || '未设置' }} · 分值：{{ q.score }}
        </p>
      </div>

      <button
        v-if="!isTeacher && !exam.attempted && !submitted"
        class="primary"
        :disabled="submitting"
        @click="submit(false)"
      >
        {{ submitting ? '提交中...' : '提交试卷' }}
      </button>

      <article v-if="result" class="score-result">
        <h3>提交成功</h3>
        <p v-if="result.is_result_published">得分：{{ result.total_score }} / {{ result.max_score }}</p>
        <p v-else>{{ result.message || '已提交，等待老师阅卷/发布成绩' }}</p>
      </article>

      <p v-if="exam.attempted && !result && !isTeacher" class="muted">你已提交该试卷，可在仪表盘查看成绩。</p>
      <p v-if="error" class="error">{{ error }}</p>
    </article>
  </section>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'

import { api } from '../api'
import BackButton from '../components/BackButton.vue'
import { authState } from '../stores/auth'

const route = useRoute()
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
    startCountdown()
  } catch (err) {
    error.value = err?.response?.data?.error || '加载试卷失败'
  } finally {
    loading.value = false
  }
}

const submit = async (autoSubmit = false) => {
  if (submitting.value || isTeacher.value || exam.attempted || submitted.value) {
    return
  }

  submitting.value = true
  error.value = ''

  try {
    const response = await api.post(`/exams/${examId}/submit/`, {
      answers,
    })
    result.value = response.data
    exam.attempted = true
    localStorage.removeItem(getTimerStorageKey())
    clearCountdown()

    if (autoSubmit) {
      error.value = '时间到，系统已自动交卷。'
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
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.45rem;
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 0.45rem 0.6rem;
}

.choice-row input {
  width: auto;
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
