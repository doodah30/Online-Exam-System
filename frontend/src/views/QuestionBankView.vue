<template>
  <section class="stack-lg">
    <article class="panel row-between">
      <div>
        <h2>题库管理（共享）</h2>
        <p class="muted">全体老师共享题库；仅创建者可编辑/删除自己的题目。</p>
      </div>
      <div class="row-wrap">
        <BackButton />
        <button class="ghost" @click="loadItems">刷新</button>
      </div>
    </article>

    <article class="panel row-wrap">
      <button class="ghost" :class="{ active: mode === 'create' }" @click="mode = 'create'">新增题目</button>
      <button class="ghost" :class="{ active: mode === 'list' }" @click="mode = 'list'">题库列表</button>
    </article>

    <article v-if="mode === 'create'" class="panel stack">
      <h3>{{ editId ? '编辑题目' : '新增题目' }}</h3>

      <form class="stack" @submit.prevent="saveItem">
        <div class="grid two-col">
          <label>
            科目标签（来自课程 + common）
            <select v-model="form.subject_tag">
              <option v-for="subject in subjectOptions" :key="subject" :value="subject">{{ subject }}</option>
            </select>
          </label>
          <label>
            难度指数（1-5）
            <input v-model.number="form.difficulty" type="number" min="1" max="5" required />
          </label>
        </div>

        <div class="grid two-col">
          <label>
            题型
            <select v-model="form.question_type">
              <option value="single">单选题</option>
              <option value="multiple">多选题</option>
              <option value="judge">判断题</option>
              <option value="short">简答题</option>
            </select>
          </label>
          <label>
            分值
            <input v-model.number="form.score" type="number" min="1" />
          </label>
        </div>

        <label>
          题干
          <textarea v-model.trim="form.text" rows="2" required></textarea>
        </label>

        <template v-if="form.question_type === 'single' || form.question_type === 'multiple'">
          <div class="row-wrap">
            <button class="ghost" type="button" @click="addOption">新增选项</button>
            <button class="ghost" type="button" :disabled="form.options.length <= 2" @click="removeOption">删除最后一个选项</button>
          </div>

          <div class="grid two-col">
            <label v-for="(opt, idx) in form.options" :key="idx">
              选项 {{ optionLabel(idx) }}
              <input v-model.trim="form.options[idx]" required />
            </label>
          </div>

          <label v-if="form.question_type === 'single'">
            正确选项
            <select v-model.number="form.correct_option">
              <option v-for="(_, idx) in form.options" :key="`single-opt-${idx}`" :value="idx">
                {{ optionLabel(idx) }}
              </option>
            </select>
          </label>

          <div v-else class="stack-sm">
            <p class="tiny">正确选项（可多选）</p>
            <label v-for="(_, idx) in form.options" :key="`co-${idx}`" class="tiny checkbox-line">
              <input type="checkbox" :value="idx" v-model="form.correct_options" />
              {{ optionLabel(idx) }}
            </label>
          </div>
        </template>

        <template v-else-if="form.question_type === 'judge'">
          <label>
            正确答案
            <select v-model.number="form.correct_option">
              <option :value="0">正确</option>
              <option :value="1">错误</option>
            </select>
          </label>
        </template>

        <template v-else>
          <label>
            参考答案
            <textarea v-model.trim="form.reference_answer" rows="2"></textarea>
          </label>
        </template>

        <div class="stack-sm">
          <p class="tiny">标签（可输入新标签，也可点击热门标签）</p>
          <div class="row-wrap">
            <span v-for="tag in selectedTags" :key="tag" class="tag-chip selected">
              {{ tag }}
              <button type="button" class="chip-x" @click="removeTag(tag)">x</button>
            </span>
            <input v-model.trim="tagInput" placeholder="输入标签后回车添加" @keyup.enter.prevent="addTag(tagInput)" />
            <button class="ghost" type="button" @click="addTag(tagInput)">添加标签</button>
          </div>

          <div class="row-wrap">
            <span class="tiny">热门标签：</span>
            <button
              v-for="hot in hotTags"
              :key="hot.tag"
              type="button"
              class="tag-chip"
              @click="addTag(hot.tag)"
            >
              {{ hot.tag }} ({{ hot.count }})
            </button>
          </div>
        </div>

        <div class="row-wrap">
          <button class="primary">{{ editId ? '保存修改' : '加入题库' }}</button>
          <button class="ghost" type="button" @click="resetForm">清空</button>
        </div>
      </form>
    </article>

    <article v-else class="panel stack">
      <div class="toolbar">
        <h3>题库列表</h3>
        <div class="toolbar-controls">
          <input class="mini-input" v-model.trim="filters.q" placeholder="搜索题干" @keyup.enter="loadItems" />
          <select class="mini-select" v-model="filters.subject_tag">
            <option value="">全部科目</option>
            <option v-for="subject in subjectOptions" :key="`f-${subject}`" :value="subject">{{ subject }}</option>
          </select>
          <select class="mini-select" v-model="filters.question_type">
            <option value="">全部题型</option>
            <option value="single">单选</option>
            <option value="multiple">多选</option>
            <option value="judge">判断</option>
            <option value="short">简答</option>
          </select>
          <button class="ghost" @click="loadItems">搜索</button>
          <button class="ghost" @click="resetFilters">重置</button>
          <button class="primary" @click="mode = 'create'">新增题目</button>
        </div>
      </div>

      <SkeletonBlock v-if="loading" :rows="4" />

      <EmptyState
        v-else-if="items.length === 0"
        title="题库还是空的"
        description="先创建一道题目，后续组卷和筛选才会更高效。"
        action-text="立即创建"
        @action="mode = 'create'"
      />

      <div v-else class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th>序号</th>
              <th>题干</th>
              <th>题型</th>
              <th>科目/标签</th>
              <th>难度</th>
              <th>分值</th>
              <th>归属</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(item, index) in items" :key="item.id">
              <td>{{ index + 1 }}</td>
              <td>{{ item.text }}</td>
              <td>{{ questionTypeText(item.question_type) }}</td>
              <td>
                <div>{{ item.subject_tag }}</div>
                <div class="tiny">{{ item.tags || '无标签' }}</div>
              </td>
              <td>{{ item.difficulty }}</td>
              <td>{{ item.score }}</td>
              <td>
                <span class="pill" :class="item.teacher_id === auth.user.id ? 'pill-success' : 'pill-draft'">
                  {{ item.teacher_id === auth.user.id ? '我创建的' : '共享题' }}
                </span>
              </td>
              <td>
                <div class="row-wrap">
                  <button class="ghost tiny-btn" :disabled="item.teacher_id !== auth.user.id" @click="startEdit(item)">编辑</button>
                  <button class="ghost danger-lite tiny-btn" :disabled="item.teacher_id !== auth.user.id" @click="removeItem(item.id)">删除</button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <p v-if="error" class="error">{{ error }}</p>
    </article>
  </section>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'

import BackButton from '../components/BackButton.vue'
import EmptyState from '../components/EmptyState.vue'
import SkeletonBlock from '../components/SkeletonBlock.vue'
import { api } from '../api'
import { authState } from '../stores/auth'

const auth = authState
const mode = ref('create')
const loading = ref(false)
const error = ref('')
const items = ref([])
const editId = ref(null)

const hotTags = ref([])
const subjectOptions = ref(['common'])
const tagInput = ref('')
const selectedTags = ref([])

const makeForm = () => ({
  question_type: 'single',
  subject_tag: 'common',
  difficulty: 3,
  text: '',
  score: 10,
  options: ['', '', '', ''],
  correct_option: 0,
  correct_options: [0],
  reference_answer: '',
})

const form = reactive(makeForm())

const filters = reactive({
  q: '',
  subject_tag: '',
  tag: '',
  difficulty: '',
  question_type: '',
})

const resetForm = () => {
  Object.assign(form, makeForm())
  selectedTags.value = ['基础']
  tagInput.value = ''
  editId.value = null
}

const addTag = (rawTag) => {
  const tag = String(rawTag || '').trim()
  if (!tag) return
  if (!selectedTags.value.includes(tag)) {
    selectedTags.value = [...selectedTags.value, tag]
  }
  tagInput.value = ''
}

const removeTag = (tag) => {
  selectedTags.value = selectedTags.value.filter((x) => x !== tag)
}

const optionLabel = (index) => {
  const alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
  if (index < alphabet.length) return alphabet[index]
  const head = Math.floor(index / alphabet.length) - 1
  const tail = index % alphabet.length
  return `${alphabet[Math.max(0, head)]}${alphabet[tail]}`
}

const addOption = () => {
  form.options.push('')
}

const removeOption = () => {
  if (form.options.length <= 2) return
  const removedIndex = form.options.length - 1
  form.options.pop()
  if (form.correct_option >= form.options.length) {
    form.correct_option = Math.max(0, form.options.length - 1)
  }
  form.correct_options = (form.correct_options || []).filter((idx) => idx !== removedIndex)
}

const toPayload = () => {
  const qType = form.question_type
  const base = {
    question_type: qType,
    subject_tag: form.subject_tag || 'common',
    tags: selectedTags.value.join(','),
    difficulty: form.difficulty,
    text: form.text,
    score: form.score,
  }

  if (qType === 'single') {
    return {
      ...base,
      options: form.options,
      correct_option: form.correct_option,
    }
  }

  if (qType === 'multiple') {
    return {
      ...base,
      options: form.options,
      correct_options: form.correct_options,
    }
  }

  if (qType === 'judge') {
    return {
      ...base,
      correct_option: form.correct_option,
    }
  }

  return {
    ...base,
    reference_answer: form.reference_answer,
  }
}

const loadMeta = async () => {
  try {
    const res = await api.get('/question-bank/meta/')
    subjectOptions.value = res.data.subject_options
    hotTags.value = res.data.hot_tags
    if (!subjectOptions.value.includes(form.subject_tag)) {
      form.subject_tag = subjectOptions.value[0] || 'common'
    }
  } catch {
    subjectOptions.value = ['common']
    hotTags.value = []
  }
}

const loadItems = async () => {
  loading.value = true
  error.value = ''
  try {
    const params = {}
    if (filters.q) params.q = filters.q
    if (filters.subject_tag) params.subject_tag = filters.subject_tag
    if (filters.tag) params.tag = filters.tag
    if (filters.difficulty) params.difficulty = filters.difficulty
    if (filters.question_type) params.question_type = filters.question_type

    const res = await api.get('/question-bank/', { params })
    items.value = res.data
  } catch (err) {
    error.value = err?.response?.data?.error || '加载题库失败'
  } finally {
    loading.value = false
  }
}

const resetFilters = async () => {
  filters.q = ''
  filters.subject_tag = ''
  filters.tag = ''
  filters.difficulty = ''
  filters.question_type = ''
  await loadItems()
}

const saveItem = async () => {
  error.value = ''
  try {
    if (selectedTags.value.length === 0) {
      error.value = '至少选择一个标签'
      return
    }

    if (editId.value) {
      await api.put(`/question-bank/${editId.value}/`, toPayload())
    } else {
      await api.post('/question-bank/', toPayload())
    }
    resetForm()
    await loadMeta()
    await loadItems()
  } catch (err) {
    error.value = err?.response?.data?.error || '保存题目失败'
  }
}

const startEdit = (item) => {
  if (item.teacher_id !== auth.user.id) return

  editId.value = item.id
  form.question_type = item.question_type
  form.subject_tag = item.subject_tag || 'common'
  form.difficulty = item.difficulty || 3
  form.text = item.text
  form.score = item.score
  form.options = Array.isArray(item.options) && item.options.length >= 2 ? item.options : ['', '']
  form.correct_option = item.correct_option ?? 0
  form.correct_options = Array.isArray(item.correct_options) ? item.correct_options : []
  form.reference_answer = item.reference_answer || ''
  selectedTags.value = item.tags ? item.tags.split(',').map((t) => t.trim()).filter(Boolean) : []
}

const removeItem = async (id) => {
  if (!window.confirm('确认删除该题目吗？')) return
  try {
    await api.delete(`/question-bank/${id}/`)
    await loadMeta()
    await loadItems()
  } catch (err) {
    error.value = err?.response?.data?.error || '删除失败'
  }
}

const questionTypeText = (questionType) => {
  const mapping = {
    single: '单选',
    multiple: '多选',
    judge: '判断',
    short: '简答',
    subjective: '简答',
  }
  return mapping[questionType] || questionType
}

onMounted(async () => {
  await loadMeta()
  resetForm()
  await loadItems()
})
</script>

<style scoped>
.error {
  color: var(--danger);
  font-weight: 700;
}

.danger-lite {
  color: var(--danger);
}

.ghost.active {
  border-color: var(--brand);
  color: var(--brand-deep);
}

.mini-input {
  width: 220px;
}

.mini-select {
  width: 130px;
}

.tiny-btn {
  padding: 0.35rem 0.6rem;
  font-size: 0.8rem;
}

.tag-chip {
  border: 1px solid var(--line);
  background: #fff;
  border-radius: 999px;
  padding: 0.22rem 0.62rem;
  font-size: 0.82rem;
}

.tag-chip.selected {
  background: #eef8f3;
  border-color: #b8dccb;
}

.chip-x {
  border: none;
  background: transparent;
  color: var(--danger);
  margin-left: 0.3rem;
  padding: 0;
}

.checkbox-line {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
}

.checkbox-line input {
  width: auto;
}
</style>
