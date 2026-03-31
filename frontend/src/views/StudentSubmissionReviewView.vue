<template>
  <section class="stack-lg">
    <article class="panel row-between">
      <div>
        <h2>查看答卷</h2>
        <p class="muted">{{ detail.exam?.title || '加载中...' }}</p>
      </div>
      <button class="ghost" @click="goBack">返回</button>
    </article>

    <article class="panel stack" v-if="loading">加载中...</article>

    <article v-else class="panel stack">
      <p class="tiny">提交时间：{{ formatDate(detail.submitted_at) }}</p>
      <p class="tiny" v-if="detail.is_result_published">成绩：{{ detail.total_score }} / {{ detail.max_score }}</p>
      <p class="tiny muted" v-else>成绩未发布，暂不展示标准答案。</p>

      <div v-for="ans in detail.answers" :key="ans.question_id" class="card stack-sm">
        <h4>第{{ ans.question_no }}题（{{ labelType(ans.question_type) }}）</h4>
        <p>{{ ans.question_text }}</p>

        <template v-if="isChoiceType(ans.question_type)">
          <div class="stack-sm">
            <div
              v-for="(opt, idx) in normalizedOptions(ans)"
              :key="`${ans.question_id}-${idx}`"
              class="choice-chip"
              :class="optionClass(ans, idx)"
            >
              {{ letter(idx) }}. {{ opt }}
            </div>
          </div>

          <p class="tiny" v-if="detail.can_view_correct">
            正确答案：{{ correctAnswerLabel(ans) }}
            <br />
            你的答案：{{ myAnswerLabel(ans) }}
          </p>
          <p class="tiny" v-else>你的答案：{{ myAnswerLabel(ans) }}</p>
        </template>

        <template v-else>
          <p class="tiny">你的答案：{{ ans.subjective_answer || '未作答' }}</p>
          <p class="tiny" v-if="detail.can_view_correct">正确答案：{{ ans.reference_answer || '未设置' }}</p>
        </template>

        <p class="tiny">得分：{{ ans.score_awarded }} / {{ ans.full_score }}</p>
      </div>

      <p v-if="error" class="error">{{ error }}</p>
    </article>
  </section>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { api } from '../api'

const route = useRoute()
const router = useRouter()
const submissionId = route.params.submissionId

const loading = ref(false)
const error = ref('')
const detail = reactive({
  exam: null,
  submitted_at: '',
  total_score: null,
  max_score: null,
  is_result_published: false,
  can_view_correct: false,
  answers: [],
})

const loadDetail = async () => {
  loading.value = true
  error.value = ''
  try {
    const res = await api.get(`/submissions/${submissionId}/review/`)
    Object.assign(detail, res.data)
  } catch (err) {
    error.value = err?.response?.data?.error || '加载答卷失败'
  } finally {
    loading.value = false
  }
}

const isChoiceType = (qType) => ['single', 'multiple', 'judge'].includes(qType)

const normalizedOptions = (ans) => {
  if (ans.question_type === 'judge') return ['正确', '错误']
  return (ans.options || []).filter((x) => x !== null && x !== undefined && String(x).trim() !== '')
}

const optionClass = (ans, idx) => {
  const classes = []
  const isMySingle = Number(ans.selected_option) === idx
  const myMulti = Array.isArray(ans.selected_options) && ans.selected_options.includes(idx)
  const isMine = ans.question_type === 'multiple' ? myMulti : isMySingle

  const isCorrectSingle = Number(ans.correct_option) === idx
  const correctMulti = Array.isArray(ans.correct_options) && ans.correct_options.includes(idx)
  const isCorrect = ans.question_type === 'multiple' ? correctMulti : isCorrectSingle

  if (detail.can_view_correct && isCorrect) classes.push('correct')
  if (detail.can_view_correct && isMine && !isCorrect) classes.push('wrong')
  if (!detail.can_view_correct && isMine) classes.push('mine')
  return classes
}

const myAnswerLabel = (ans) => {
  if (ans.question_type === 'multiple') {
    if (!Array.isArray(ans.selected_options) || ans.selected_options.length === 0) return '未作答'
    return ans.selected_options.map((x) => letter(x)).join('、')
  }
  if (ans.question_type === 'single' || ans.question_type === 'judge') {
    if (ans.selected_option === null || ans.selected_option === undefined) return '未作答'
    if (ans.question_type === 'judge') return Number(ans.selected_option) === 0 ? '正确' : '错误'
    return letter(ans.selected_option)
  }
  return ans.subjective_answer || '未作答'
}

const correctAnswerLabel = (ans) => {
  if (ans.question_type === 'multiple') {
    if (!Array.isArray(ans.correct_options) || ans.correct_options.length === 0) return '未设置'
    return ans.correct_options.map((x) => letter(x)).join('、')
  }
  if (ans.question_type === 'single' || ans.question_type === 'judge') {
    if (ans.correct_option === null || ans.correct_option === undefined) return '未设置'
    if (ans.question_type === 'judge') return Number(ans.correct_option) === 0 ? '正确' : '错误'
    return letter(ans.correct_option)
  }
  return ans.reference_answer || '未设置'
}

const labelType = (qType) => {
  const map = {
    single: '单选题',
    multiple: '多选题',
    judge: '判断题',
    blank: '填空题',
    short: '简答题',
  }
  return map[qType] || qType
}

const letter = (idx) => {
  if (idx === 0) return 'A'
  if (idx === 1) return 'B'
  if (idx === 2) return 'C'
  if (idx === 3) return 'D'
  return String(idx)
}

const formatDate = (dateText) => (dateText ? new Date(dateText).toLocaleString() : '--')
const goBack = () => router.back()

onMounted(loadDetail)
</script>

<style scoped>
.choice-chip {
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 0.55rem 0.65rem;
  background: #fff;
}

.choice-chip.mine {
  border-color: #6f8aa3;
  background: #eef4fb;
}

.choice-chip.correct {
  border-color: #2f9f6b;
  background: #eaf9f1;
  color: #0f6b43;
  font-weight: 700;
}

.choice-chip.wrong {
  border-color: #d14a4a;
  background: #ffefef;
  color: #a42424;
  font-weight: 700;
}

.error {
  color: var(--danger);
  font-weight: 700;
}
</style>
