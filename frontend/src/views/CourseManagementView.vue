<template>
  <section class="stack-lg">
    <article class="panel row-between">
      <div>
        <h2>课程管理</h2>
        <p class="muted">将创建课程与我的课程分开，便于按流程操作。</p>
      </div>
      <button class="ghost" @click="goCenter">返回功能中心</button>
    </article>

    <article class="panel row-wrap">
      <button class="ghost" :class="{ active: mode === 'create' }" @click="mode = 'create'">创建课程</button>
      <button class="ghost" :class="{ active: mode === 'list' }" @click="mode = 'list'">我的课程</button>
    </article>

    <article v-if="mode === 'create'" class="panel stack">
      <h3>创建课程</h3>
      <form class="stack" @submit.prevent="createCourse">
        <div class="grid two-col">
          <label>
            课程名称
            <input v-model.trim="courseForm.name" required placeholder="例如：数据库原理" />
          </label>
          <label>
            课程标签
            <input v-model.trim="courseForm.subject_tag" required placeholder="例如：database，通用填 common" />
          </label>
        </div>
        <label>
          课程描述
          <input v-model.trim="courseForm.description" placeholder="可选" />
        </label>
        <button class="primary" :disabled="loadingCreate">{{ loadingCreate ? '创建中...' : '创建课程' }}</button>
      </form>
    </article>

    <article v-else class="panel stack">
      <div class="row-between">
        <h3>课程列表</h3>
        <button class="ghost" @click="loadCourses">刷新</button>
      </div>

      <p v-if="loadingList" class="muted">加载中...</p>
      <p v-else-if="courses.length === 0" class="muted">暂无课程</p>

      <div v-else class="stack-sm">
        <div v-for="course in courses" :key="course.id" class="card stack-sm">
          <div class="row-between">
            <h4>{{ course.name }}</h4>
            <div class="row-wrap">
              <router-link class="ghost" :to="`/courses/${course.id}/stats`">统计图表</router-link>
              <button class="ghost" @click="openCourse(course)">进入课程</button>
            </div>
          </div>
          <p class="tiny">标签：{{ course.subject_tag }} · 学生数：{{ course.student_count }}</p>
          <p class="tiny">{{ course.description || '暂无描述' }}</p>
        </div>
      </div>
    </article>

    <article v-if="activeCourse" class="panel stack">
      <div class="row-between">
        <h3>课程学生管理：{{ activeCourse.name }}</h3>
        <button class="ghost" @click="closeCourse">关闭</button>
      </div>

      <div class="grid two-col">
        <label>
          搜索学生
          <input v-model.trim="studentSearch" placeholder="按用户名搜索" @input="searchAllStudents" />
        </label>
        <label>
          已选人数
          <input :value="selectedUsers.size" disabled />
        </label>
      </div>

      <div class="row-wrap">
        <button class="ghost" @click="selectAllVisible">全选当前列表</button>
        <button class="ghost" @click="clearSelected">清空选择</button>
        <button class="primary" @click="addSelectedStudents">一键添加已选学生</button>
      </div>

      <div class="student-grid">
        <label v-for="stu in studentOptions" :key="stu.id" class="student-item">
          <input type="checkbox" :checked="selectedUsers.has(stu.username)" @change="toggleUser(stu.username)" />
          <span>{{ stu.username }}</span>
        </label>
      </div>

      <div class="stack-sm">
        <h4>当前课程学生</h4>
        <p v-if="courseStudents.length === 0" class="muted">暂无学生</p>
        <div class="row-wrap" v-else>
          <span v-for="stu in courseStudents" :key="stu.id" class="tag">
            {{ stu.username }}
            <button class="remove-btn" @click="removeStudent(stu.username)">x</button>
          </span>
        </div>
      </div>
    </article>

    <p v-if="error" class="error">{{ error }}</p>
  </section>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

import { api } from '../api'

const router = useRouter()

const mode = ref('create')
const courses = ref([])
const error = ref('')
const loadingCreate = ref(false)
const loadingList = ref(false)

const courseForm = reactive({
  name: '',
  subject_tag: 'common',
  description: '',
})

const activeCourse = ref(null)
const studentSearch = ref('')
const studentOptions = ref([])
const courseStudents = ref([])
const selectedUsers = ref(new Set())

const goCenter = () => router.push('/teacher')

const loadCourses = async () => {
  loadingList.value = true
  error.value = ''
  try {
    const res = await api.get('/courses/')
    courses.value = res.data
  } catch (err) {
    error.value = err?.response?.data?.error || '加载课程失败'
  } finally {
    loadingList.value = false
  }
}

const createCourse = async () => {
  loadingCreate.value = true
  error.value = ''
  try {
    await api.post('/courses/', courseForm)
    courseForm.name = ''
    courseForm.subject_tag = 'common'
    courseForm.description = ''
    mode.value = 'list'
    await loadCourses()
  } catch (err) {
    error.value = err?.response?.data?.error || '创建课程失败'
  } finally {
    loadingCreate.value = false
  }
}

const openCourse = async (course) => {
  activeCourse.value = course
  studentSearch.value = ''
  selectedUsers.value = new Set()
  await Promise.all([searchAllStudents(), loadCourseStudents()])
}

const closeCourse = () => {
  activeCourse.value = null
  courseStudents.value = []
  studentOptions.value = []
  selectedUsers.value = new Set()
}

const searchAllStudents = async () => {
  if (!activeCourse.value) return
  try {
    const res = await api.get('/students/', { params: { q: studentSearch.value } })
    studentOptions.value = res.data
  } catch (err) {
    error.value = err?.response?.data?.error || '搜索学生失败'
  }
}

const loadCourseStudents = async () => {
  if (!activeCourse.value) return
  try {
    const res = await api.get(`/courses/${activeCourse.value.id}/students/`)
    courseStudents.value = res.data.students
  } catch (err) {
    error.value = err?.response?.data?.error || '加载课程学生失败'
  }
}

const toggleUser = (username) => {
  const copied = new Set(selectedUsers.value)
  if (copied.has(username)) copied.delete(username)
  else copied.add(username)
  selectedUsers.value = copied
}

const selectAllVisible = () => {
  const copied = new Set(selectedUsers.value)
  studentOptions.value.forEach((stu) => copied.add(stu.username))
  selectedUsers.value = copied
}

const clearSelected = () => {
  selectedUsers.value = new Set()
}

const addSelectedStudents = async () => {
  if (!activeCourse.value || selectedUsers.value.size === 0) return
  try {
    await api.post(`/courses/${activeCourse.value.id}/students/`, {
      action: 'add',
      usernames: Array.from(selectedUsers.value),
    })
    await Promise.all([loadCourseStudents(), loadCourses()])
    selectedUsers.value = new Set()
  } catch (err) {
    error.value = err?.response?.data?.error || '添加学生失败'
  }
}

const removeStudent = async (username) => {
  if (!activeCourse.value) return
  try {
    await api.post(`/courses/${activeCourse.value.id}/students/`, {
      action: 'remove',
      username,
    })
    await Promise.all([loadCourseStudents(), loadCourses()])
  } catch (err) {
    error.value = err?.response?.data?.error || '移除学生失败'
  }
}

onMounted(loadCourses)
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

.student-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.5rem;
}

.student-item {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 0.35rem 0.5rem;
}

.student-item input {
  width: auto;
}

.tag {
  display: inline-flex;
  gap: 0.4rem;
  align-items: center;
  border: 1px solid var(--line);
  border-radius: 999px;
  padding: 0.2rem 0.55rem;
}

.remove-btn {
  border: none;
  padding: 0;
  background: transparent;
  color: var(--danger);
  cursor: pointer;
  font-weight: 700;
}

@media (max-width: 900px) {
  .student-grid {
    grid-template-columns: 1fr;
  }
}
</style>
