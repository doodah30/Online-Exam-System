<template>
  <section class="stack-lg">
    <article class="panel row-between">
      <div>
        <h2>试卷管理</h2>
        <p class="muted">创建试卷与阅卷入口分开，减少单页复杂度。</p>
      </div>
      <button class="ghost" @click="goCenter">返回功能中心</button>
    </article>

    <article class="panel row-wrap">
      <button class="ghost" :class="{ active: mode === 'create' }" @click="mode = 'create'">创建试卷</button>
      <button class="ghost" :class="{ active: mode === 'list' }" @click="mode = 'list'">我的试卷 / 阅卷</button>
    </article>

    <article v-if="mode === 'create'" class="panel stack">
      <h3>创建试卷</h3>

      <form class="stack" @submit.prevent="createExam">
        <div class="grid two-col">
          <label>
            试卷标题
            <input v-model.trim="examForm.title" required />
          </label>
          <label>
            考试时长（分钟）
            <input v-model.number="examForm.duration_minutes" type="number" min="1" required />
          </label>
        </div>

        <div class="grid two-col">
          <label>
            课程（决定可见学生）
            <select v-model="examForm.course_id">
              <option value="">不绑定课程（所有学生可见）</option>
              <option v-for="c in courses" :key="c.id" :value="c.id">{{ c.name }}（{{ c.subject_tag }}）</option>
            </select>
          </label>
          <label>
            成绩发布策略
            <select v-model="examForm.result_policy">
              <option value="teacher_release">老师统一发布（推荐）</option>
              <option value="auto_release">自动发布（仅客观题）</option>
            </select>
          </label>
        </div>

        <label>
          试卷描述
          <textarea v-model.trim="examForm.description" rows="2"></textarea>
        </label>

        <div class="row-wrap">
          <button class="ghost" type="button" @click="goPickQuestions">去题库选题</button>
          <button class="ghost" type="button" @click="addManualQuestion">手动加题</button>
          <button class="ghost" type="button" @click="clearDraft">清空草稿</button>
        </div>

        <div v-if="examForm.questions.length > 0" class="row-wrap">
          <label>
            批量改分
            <input v-model.number="batchScore" type="number" min="1" placeholder="分值" />
          </label>
          <button class="ghost" type="button" @click="applyBatchScore">应用到勾选题目</button>
        </div>

        <p v-if="examForm.questions.length === 0" class="muted">当前还没有题目，请先添加或从题库选题。</p>

        <div
          v-for="(q, idx) in examForm.questions"
          :key="q.localId"
          class="card compact-question"
          draggable="true"
          @dragstart="onDragStart(idx)"
          @dragover.prevent
          @drop="onDrop(idx)"
        >
          <div class="row-between">
            <div>
              <label class="tiny checkbox-line">
                <input type="checkbox" v-model="selectedQuestionIds" :value="q.localId" />
                第 {{ idx + 1 }} 题
              </label>
              <h4>{{ q.text || '未填写题干' }}</h4>
              <p class="tiny">科目：{{ q.subject_tag || 'common' }} · 标签：{{ q.tags || '无' }} · 分值：{{ q.score }}</p>
            </div>
            <div class="row-wrap">
              <button class="ghost" type="button" @click="openDetail(q.localId)">详情</button>
              <button class="ghost" type="button" @click="removeQuestion(idx)">删除</button>
            </div>
          </div>

          <div v-if="editingQuestionId === q.localId" class="panel stack editor-panel inline-editor">
            <div class="row-between">
              <h4>编辑题目详情</h4>
              <button class="ghost" type="button" @click="closeDetail">关闭详情</button>
            </div>

            <div class="grid two-col">
              <label>
                题型
                <select v-model="q.question_type">
                  <option value="single">单选题</option>
                  <option value="multiple">多选题</option>
                  <option value="judge">判断题</option>
                  <option value="blank">填空题</option>
                  <option value="short">简答题</option>
                </select>
              </label>
              <label>
                分值
                <input v-model.number="q.score" type="number" min="1" required />
              </label>
            </div>

            <label>
              题干
              <textarea v-model.trim="q.text" rows="2" required></textarea>
            </label>

            <template v-if="q.question_type === 'single' || q.question_type === 'multiple'">
              <div class="grid two-col">
                <label v-for="(opt, i) in q.options" :key="i">
                  选项 {{ String.fromCharCode(65 + i) }}
                  <input v-model.trim="q.options[i]" required />
                </label>
              </div>

              <label v-if="q.question_type === 'single'">
                正确选项
                <select v-model.number="q.correct_option">
                  <option :value="0">A</option>
                  <option :value="1">B</option>
                  <option :value="2">C</option>
                  <option :value="3">D</option>
                </select>
              </label>

              <div v-else class="stack-sm">
                <p class="tiny">正确选项（可多选）</p>
                <label v-for="opt in [0, 1, 2, 3]" :key="`${q.localId}-co-${opt}`" class="tiny checkbox-line">
                  <input type="checkbox" :value="opt" v-model="q.correct_options" />
                  {{ String.fromCharCode(65 + opt) }}
                </label>
              </div>
            </template>

            <template v-else-if="q.question_type === 'judge'">
              <label>
                正确答案
                <select v-model.number="q.correct_option">
                  <option :value="0">正确</option>
                  <option :value="1">错误</option>
                </select>
              </label>
            </template>

            <template v-else>
              <label>
                参考答案
                <textarea v-model.trim="q.reference_answer" rows="2"></textarea>
              </label>
              <label>
                关键词（逗号分隔）
                <input v-model.trim="q.keyword_answers" />
              </label>
            </template>

            <div class="grid two-col">
              <label>
                科目标签
                <input v-model.trim="q.subject_tag" />
              </label>
              <label>
                难度（1-5）
                <input v-model.number="q.difficulty" type="number" min="1" max="5" />
              </label>
            </div>

            <label class="save-row">
              <span>保存到题库</span>
              <input type="checkbox" v-model="q.save_to_bank" />
            </label>

            <label>
              标签（逗号分隔）
              <input v-model.trim="q.tags" />
            </label>
          </div>
        </div>

        <button class="primary" :disabled="loadingCreate || examForm.questions.length === 0">
          {{ loadingCreate ? '发布中...' : '发布试卷' }}
        </button>
      </form>
    </article>

    <article v-else class="panel stack">
      <div class="row-between">
        <h3>我创建的试卷</h3>
        <div class="row-wrap">
          <select v-model="examSubjectFilter">
            <option value="">全部科目</option>
            <option value="common">common</option>
            <option v-for="c in courses" :key="`sub-${c.id}`" :value="c.subject_tag">{{ c.subject_tag }}</option>
          </select>
          <button class="ghost" @click="loadExams">刷新</button>
        </div>
      </div>

      <p v-if="loadingExams" class="muted">加载中...</p>
      <p v-else-if="filteredExams.length === 0" class="muted">暂无试卷</p>

      <div v-else class="stack-sm">
        <div v-for="exam in filteredExams" :key="exam.id" class="card exam-row">
          <div>
            <h4>{{ exam.title }}</h4>
            <p class="tiny">题目数：{{ exam.question_count }} · 时长：{{ exam.duration_minutes }} 分钟 · 课程：{{ exam.course?.name || '无' }}</p>
          </div>
          <div class="row-wrap">
            <button class="ghost" @click="goExam(exam.id)">查看试卷</button>
            <button class="ghost" @click="goSubmissions(exam.id)">进入阅卷</button>
          </div>
        </div>
      </div>
    </article>

    <p v-if="error" class="error">{{ error }}</p>
  </section>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

import { api } from '../api'

const router = useRouter()
const mode = ref('create')

const DRAFT_KEY = 'teacher_exam_draft'

const exams = ref([])
const courses = ref([])
const examSubjectFilter = ref('')
const error = ref('')
const loadingCreate = ref(false)
const loadingExams = ref(false)

let idSeed = 1
const makeQuestion = () => ({
  localId: idSeed++,
  question_type: 'single',
  text: '',
  options: ['', '', '', ''],
  correct_option: 0,
  correct_options: [0],
  reference_answer: '',
  keyword_answers: '',
  subject_tag: 'common',
  tags: '',
  difficulty: 3,
  score: 10,
  save_to_bank: false,
  bank_item_id: null,
})

const examForm = reactive({
  title: '',
  description: '',
  duration_minutes: 60,
  course_id: '',
  result_policy: 'teacher_release',
  questions: [],
})

const selectedQuestionIds = ref([])
const batchScore = ref(null)
const dragFromIndex = ref(-1)
const editingQuestionId = ref(null)

const filteredExams = computed(() => {
  if (!examSubjectFilter.value) return exams.value
  return exams.value.filter((exam) => (exam.course?.subject_tag || 'common') === examSubjectFilter.value)
})

const goCenter = () => router.push('/teacher')

const saveDraft = () => {
  localStorage.setItem(DRAFT_KEY, JSON.stringify(examForm))
}

const loadDraft = () => {
  const raw = localStorage.getItem(DRAFT_KEY)
  if (!raw) return
  try {
    const parsed = JSON.parse(raw)
    Object.assign(examForm, parsed)
    examForm.questions = (parsed.questions || []).map((q) => ({ ...makeQuestion(), ...q }))
  } catch {
    localStorage.removeItem(DRAFT_KEY)
  }
}

watch(
  examForm,
  () => {
    saveDraft()
  },
  { deep: true },
)

const clearDraft = () => {
  examForm.title = ''
  examForm.description = ''
  examForm.duration_minutes = 60
  examForm.course_id = ''
  examForm.result_policy = 'teacher_release'
  examForm.questions = []
  selectedQuestionIds.value = []
  editingQuestionId.value = null
  localStorage.removeItem(DRAFT_KEY)
}

const addManualQuestion = () => {
  const q = makeQuestion()
  const course = courses.value.find((c) => String(c.id) === String(examForm.course_id))
  if (course) q.subject_tag = course.subject_tag
  examForm.questions.push(q)
  editingQuestionId.value = q.localId
}

const removeQuestion = (index) => {
  selectedQuestionIds.value = selectedQuestionIds.value.filter(
    (id) => id !== examForm.questions[index].localId,
  )
  if (editingQuestionId.value === examForm.questions[index].localId) {
    editingQuestionId.value = null
  }
  examForm.questions.splice(index, 1)
}

const openDetail = (localId) => {
  editingQuestionId.value = localId
}

const closeDetail = () => {
  editingQuestionId.value = null
}

const applyBatchScore = () => {
  const score = Number(batchScore.value)
  if (!score || score <= 0) return
  examForm.questions.forEach((q) => {
    if (selectedQuestionIds.value.includes(q.localId)) {
      q.score = score
    }
  })
}

const onDragStart = (index) => {
  dragFromIndex.value = index
}

const onDrop = (targetIndex) => {
  const sourceIndex = dragFromIndex.value
  dragFromIndex.value = -1
  if (sourceIndex < 0 || sourceIndex === targetIndex) return

  const moved = examForm.questions.splice(sourceIndex, 1)[0]
  examForm.questions.splice(targetIndex, 0, moved)
}

const goPickQuestions = () => {
  saveDraft()
  const course = courses.value.find((c) => String(c.id) === String(examForm.course_id))
  if (course) {
    router.push(`/question-picker?subject=${encodeURIComponent(course.subject_tag)}`)
    return
  }
  router.push('/question-picker')
}

const appendPickedQuestions = async () => {
  const raw = localStorage.getItem('exam_picker_selected')
  if (!raw) return

  let ids = []
  try {
    ids = JSON.parse(raw)
  } catch {
    localStorage.removeItem('exam_picker_selected')
    return
  }

  if (!Array.isArray(ids) || ids.length === 0) {
    localStorage.removeItem('exam_picker_selected')
    return
  }

  const res = await api.get('/question-bank/')
  const map = new Map(res.data.map((x) => [x.id, x]))

  ids.forEach((id) => {
    const item = map.get(id)
    if (!item) return
    const q = makeQuestion()
    q.question_type = item.question_type
    q.text = item.text
    q.score = item.score
    q.options = item.options || ['', '', '', '']
    q.correct_option = item.correct_option ?? 0
    q.correct_options = Array.isArray(item.correct_options) ? item.correct_options : []
    q.reference_answer = item.reference_answer || ''
    q.keyword_answers = item.keyword_answers || ''
    q.subject_tag = item.subject_tag || 'common'
    q.tags = item.tags || ''
    q.difficulty = item.difficulty || 3
    q.bank_item_id = item.id
    examForm.questions.push(q)
  })

  localStorage.removeItem('exam_picker_selected')
}

const normalizeQuestion = (q) => {
  const base = {
    question_type: q.question_type,
    text: q.text,
    score: q.score,
    save_to_bank: q.save_to_bank,
    subject_tag: q.subject_tag || 'common',
    tags: q.tags || '',
    difficulty: q.difficulty || 3,
  }

  if (q.bank_item_id) return { ...base, bank_item_id: q.bank_item_id }

  if (q.question_type === 'single') {
    return { ...base, options: q.options, correct_option: q.correct_option }
  }

  if (q.question_type === 'multiple') {
    return { ...base, options: q.options, correct_options: q.correct_options || [] }
  }

  if (q.question_type === 'judge') {
    return { ...base, correct_option: q.correct_option }
  }

  return {
    ...base,
    reference_answer: q.reference_answer,
    keyword_answers: q.keyword_answers,
  }
}

const createExam = async () => {
  loadingCreate.value = true
  error.value = ''
  try {
    await api.post('/exams/', {
      title: examForm.title,
      description: examForm.description,
      duration_minutes: examForm.duration_minutes,
      course_id: examForm.course_id || null,
      result_policy: examForm.result_policy,
      is_published: true,
      questions: examForm.questions.map(normalizeQuestion),
    })
    clearDraft()
    mode.value = 'list'
    await loadExams()
  } catch (err) {
    error.value = err?.response?.data?.error || '创建试卷失败'
  } finally {
    loadingCreate.value = false
  }
}

const loadExams = async () => {
  loadingExams.value = true
  error.value = ''
  try {
    const res = await api.get('/exams/')
    exams.value = res.data
  } catch (err) {
    error.value = err?.response?.data?.error || '加载试卷失败'
  } finally {
    loadingExams.value = false
  }
}

const loadCourses = async () => {
  const res = await api.get('/courses/')
  courses.value = res.data
}

const goExam = (id) => router.push(`/exams/${id}`)
const goSubmissions = (id) => router.push(`/exams/${id}/submissions`)

onMounted(async () => {
  await loadCourses()
  loadDraft()
  await appendPickedQuestions()
  await loadExams()
})
</script>

<style scoped>
.error {
  color: var(--danger);
  font-weight: 700;
}

.ghost.active {
  border-color: var(--brand);
  color: var(--brand-deep);
}

.compact-question {
  border: 1px dashed #c7dbcc;
  background: #fbfffc;
}

.checkbox-line {
  display: flex;
  gap: 0.35rem;
  align-items: center;
}

.checkbox-line input,
.save-row input {
  width: auto;
}

.editor-panel {
  border: 1px solid #d9e8de;
  background: #f7fcf9;
}

.inline-editor {
  margin-top: 0.7rem;
}

.save-row {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
}
</style>
