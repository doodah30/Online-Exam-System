import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'
import AuthView from '../views/AuthView.vue'
import DashboardView from '../views/DashboardView.vue'
import StudentExamsView from '../views/StudentExamsView.vue'
import StudentScoresView from '../views/StudentScoresView.vue'
import StudentSubmissionReviewView from '../views/StudentSubmissionReviewView.vue'
import AdminHomeView from '../views/AdminHomeView.vue'
import AdminUsersView from '../views/AdminUsersView.vue'
import AdminLogsView from '../views/AdminLogsView.vue'
import AdminExamControlView from '../views/AdminExamControlView.vue'
import AdminSystemConfigView from '../views/AdminSystemConfigView.vue'
import AdminChangePasswordView from '../views/AdminChangePasswordView.vue'
import TeacherHomeView from '../views/TeacherHomeView.vue'
import CourseManagementView from '../views/CourseManagementView.vue'
import ExamManagementView from '../views/ExamManagementView.vue'
import QuestionPickerView from '../views/QuestionPickerView.vue'
import ExamDetailView from '../views/ExamDetailView.vue'
import ExamSubmissionsView from '../views/ExamSubmissionsView.vue'
import QuestionBankView from '../views/QuestionBankView.vue'
import CourseStatsView from '../views/CourseStatsView.vue'
import EmailBindingView from '../views/EmailBindingView.vue'
import { authState } from '../stores/auth'

// 路由定义：根据角色区分老师与学生可访问页面。
const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomeView,
    },
    {
      path: '/auth',
      name: 'auth',
      component: AuthView,
    },
    {
      path: '/dashboard',
      name: 'dashboard',
      component: DashboardView,
      meta: { requiresAuth: true },
    },
    {
      path: '/student/exams',
      name: 'student-exams',
      component: StudentExamsView,
      meta: { requiresAuth: true, role: 'student' },
    },
    {
      path: '/student/scores',
      name: 'student-scores',
      component: StudentScoresView,
      meta: { requiresAuth: true, role: 'student' },
    },
    {
      path: '/submissions/:submissionId/review',
      name: 'student-submission-review',
      component: StudentSubmissionReviewView,
      meta: { requiresAuth: true, role: 'student' },
    },
    {
      path: '/admin',
      name: 'admin-home',
      component: AdminHomeView,
      meta: { requiresAuth: true, role: 'admin' },
    },
    {
      path: '/admin/users',
      name: 'admin-users',
      component: AdminUsersView,
      meta: { requiresAuth: true, role: 'admin' },
    },
    {
      path: '/admin/logs',
      name: 'admin-logs',
      component: AdminLogsView,
      meta: { requiresAuth: true, role: 'admin' },
    },
    {
      path: '/admin/exams',
      name: 'admin-exams',
      component: AdminExamControlView,
      meta: { requiresAuth: true, role: 'admin' },
    },
    {
      path: '/admin/system-config',
      name: 'admin-system-config',
      component: AdminSystemConfigView,
      meta: { requiresAuth: true, role: 'admin' },
    },
    {
      path: '/admin/change-password',
      name: 'admin-change-password',
      component: AdminChangePasswordView,
      meta: { requiresAuth: true, role: 'admin' },
    },
    {
      path: '/teacher',
      name: 'teacher-home',
      component: TeacherHomeView,
      meta: { requiresAuth: true, role: 'teacher' },
    },
    {
      path: '/course-management',
      name: 'course-management',
      component: CourseManagementView,
      meta: { requiresAuth: true, role: 'teacher' },
    },
    {
      path: '/exam-management',
      name: 'exam-management',
      component: ExamManagementView,
      meta: { requiresAuth: true, role: 'teacher' },
    },
    {
      path: '/question-picker',
      name: 'question-picker',
      component: QuestionPickerView,
      meta: { requiresAuth: true, role: 'teacher' },
    },
    {
      path: '/exams/:id',
      name: 'exam-detail',
      component: ExamDetailView,
      meta: { requiresAuth: true },
    },
    {
      path: '/exams/:id/submissions',
      name: 'exam-submissions',
      component: ExamSubmissionsView,
      meta: { requiresAuth: true, role: 'teacher' },
    },
    {
      path: '/question-bank',
      name: 'question-bank',
      component: QuestionBankView,
      meta: { requiresAuth: true, role: 'teacher' },
    },
    {
      path: '/courses/:id/stats',
      name: 'course-stats',
      component: CourseStatsView,
      meta: { requiresAuth: true, role: 'teacher' },
    },
    {
      path: '/account/email',
      name: 'account-email',
      component: EmailBindingView,
      meta: { requiresAuth: true },
    },
    {
      path: '/:pathMatch(.*)*',
      redirect: '/',
    },
  ],
})

router.beforeEach((to) => {
  // 规则 1：需要登录但未登录 -> 跳转到登录页。
  if (to.meta.requiresAuth && !authState.isAuthenticated) {
    return '/auth'
  }

  // 规则 2：已登录用户不再进入登录页。
  if (to.path === '/auth' && authState.isAuthenticated) {
    if (authState.user.role === 'teacher') return '/teacher'
    if (authState.user.role === 'admin') return '/admin'
    return '/dashboard'
  }

  // 规则 3：角色不匹配（例如学生访问老师页）-> 回到仪表盘。
  if (to.meta.role && authState.user.role !== to.meta.role) {
    if (authState.user.role === 'teacher') return '/teacher'
    if (authState.user.role === 'admin') return '/admin'
    return '/dashboard'
  }

  return true
})

export default router
