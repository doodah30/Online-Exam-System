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

      <SkeletonBlock v-if="loadingList" :rows="3" />
      <EmptyState
        v-else-if="courses.length === 0"
        title="还没有课程"
        description="先创建第一门课程，再去添加学生和发布考试。"
        action-text="去创建课程"
        @action="mode = 'create'"
      />

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

      <div class="toolbar">
        <h4>学生列表</h4>
        <div class="toolbar-controls">
          <input class="mini-input" v-model.trim="studentSearch" placeholder="按用户名搜索" @input="searchAllStudents" />
          <button class="ghost" @click="selectAllVisible">全选当前页</button>
          <button class="ghost" @click="clearSelected">清空选择</button>
          <button class="primary" @click="addSelectedStudents">添加已选（{{ selectedUsers.size }}）</button>
        </div>
      </div>

      <SkeletonBlock v-if="loadingStudents" :rows="2" />
      <div v-else-if="studentOptions.length" class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th>选择</th>
              <th>用户ID</th>
              <th>用户名</th>
              <th>状态</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="stu in studentOptions" :key="stu.id">
              <td>
                <input type="checkbox" :checked="selectedUsers.has(stu.username)" @change="toggleUser(stu.username)" />
              </td>
              <td>#{{ stu.id }}</td>
              <td>{{ stu.username }}</td>
              <td>
                <span class="pill pill-success">可添加</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <EmptyState v-else title="没有匹配学生" description="试试更短的关键字，或先在管理员端创建学生账号。" />

      <div class="stack-sm">
        <h4>当前课程学生</h4>
        <EmptyState
          v-if="courseStudents.length === 0"
          title="课程还没有学生"
          description="请先从上方列表勾选学生并添加到课程。"
        />
        <div v-else class="table-wrap">
          <table class="data-table">
            <thead>
              <tr>
                <th>用户ID</th>
                <th>用户名</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="stu in courseStudents" :key="stu.id">
                <td>#{{ stu.id }}</td>
                <td>{{ stu.username }}</td>
                <td>
                  <button class="ghost danger-lite tiny-btn" @click="removeStudent(stu.username)">移出课程</button>
                </td>
              </tr>
            </tbody>
          </table>
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
import EmptyState from '../components/EmptyState.vue'
import SkeletonBlock from '../components/SkeletonBlock.vue'

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
const loadingStudents = ref(false)

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
  loadingStudents.value = true
  try {
    const res = await api.get('/students/', { params: { q: studentSearch.value } })
    studentOptions.value = res.data
  } catch (err) {
    error.value = err?.response?.data?.error || '搜索学生失败'
  } finally {
    loadingStudents.value = false
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

.danger-lite {
  color: var(--danger);
}


.mini-input {
  width: 220px;
}

.tiny-btn {
  padding: 0.35rem 0.6rem;
  font-size: 0.8rem;
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

</style>
