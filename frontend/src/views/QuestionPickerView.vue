<template>
  <section class="stack-lg">
    <article class="panel row-between">
      <div>
        <h2>题库选题</h2>
        <p class="muted">支持按科目标签、题型、标签、难度筛选并批量勾选。</p>
      </div>
      <BackButton />
    </article>

    <article class="panel stack">
      <div class="grid two-col">
        <label>
          搜索关键字
          <input v-model.trim="filter.q" placeholder="搜索题干" />
        </label>
        <label>
          科目标签
          <input v-model.trim="filter.subject_tag" placeholder="例如：database 或 common" />
        </label>
      </div>

      <div class="grid two-col">
        <label>
          普通标签
          <input v-model.trim="filter.tag" placeholder="例如：基础,SQL" />
        </label>
        <label>
          难度（1-5）
          <select v-model="filter.difficulty">
            <option value="">全部</option>
            <option v-for="n in 5" :key="n" :value="n">{{ n }}</option>
          </select>
        </label>
      </div>

      <div class="row-wrap">
        <button class="ghost" @click="loadItems">筛选</button>
        <button class="ghost" @click="clearFilter">清空</button>
      </div>
    </article>

    <article class="panel stack">
      <div class="row-between">
        <h3>题目列表</h3>
        <button class="primary" @click="confirmPick">完成选题（{{ selectedIds.size }}）</button>
      </div>

      <p v-if="loading" class="muted">加载中...</p>
      <p v-else-if="items.length === 0" class="muted">暂无匹配题目</p>

      <div v-else class="stack-sm">
        <label v-for="(item, idx) in items" :key="item.id" class="card pick-row">
          <input type="checkbox" :checked="selectedIds.has(item.id)" @change="toggle(item.id)" />
          <div>
            <h4>#{{ idx + 1 }} {{ item.text }}</h4>
            <p class="tiny">创建者：{{ item.teacher_username }} · 科目：{{ item.subject_tag }} · 标签：{{ item.tags || '无' }} · 难度：{{ item.difficulty }}</p>
          </div>
        </label>
      </div>

      <p v-if="error" class="error">{{ error }}</p>
    </article>
  </section>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { api } from '../api'
import BackButton from '../components/BackButton.vue'

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const error = ref('')
const items = ref([])
const selectedIds = ref(new Set())

const filter = reactive({
  q: '',
  subject_tag: route.query.subject || '',
  tag: '',
  difficulty: '',
})

const loadItems = async () => {
  loading.value = true
  error.value = ''

  try {
    const params = {}
    if (filter.q) params.q = filter.q
    if (filter.subject_tag) params.subject_tag = filter.subject_tag
    if (filter.tag) params.tag = filter.tag
    if (filter.difficulty) params.difficulty = filter.difficulty

    const res = await api.get('/question-bank/', { params })
    items.value = res.data
  } catch (err) {
    error.value = err?.response?.data?.error || '加载题库失败'
  } finally {
    loading.value = false
  }
}

const clearFilter = async () => {
  filter.q = ''
  filter.subject_tag = ''
  filter.tag = ''
  filter.difficulty = ''
  await loadItems()
}

const toggle = (id) => {
  const copied = new Set(selectedIds.value)
  if (copied.has(id)) copied.delete(id)
  else copied.add(id)
  selectedIds.value = copied
}

const confirmPick = () => {
  localStorage.setItem('exam_picker_selected', JSON.stringify(Array.from(selectedIds.value)))
  router.replace('/exam-management')
}

onMounted(loadItems)
</script>

<style scoped>
.pick-row {
  display: flex;
  align-items: flex-start;
  gap: 0.7rem;
}

.pick-row input {
  width: auto;
  margin-top: 0.35rem;
}

.error {
  color: var(--danger);
  font-weight: 700;
}
</style>
