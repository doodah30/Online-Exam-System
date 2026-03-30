import { reactive } from 'vue'

// 页面刷新后仍能保持登录态：
// - exam_token: 后端签发的 token
// - exam_user: 前端缓存的用户基本信息（id/username/role）
const storedUser = localStorage.getItem('exam_user')
const storedToken = localStorage.getItem('exam_token')

export const authState = reactive({
  token: storedToken || '',
  user: storedUser
    ? JSON.parse(storedUser)
    : {
        id: null,
        username: '',
        role: '',
        email: '',
      },
  isAuthenticated: Boolean(storedToken),
})

export function setAuth(payload) {
  // 登录/注册成功后更新内存状态 + 本地缓存。
  authState.token = payload.token
  authState.user = {
    id: payload?.user?.id ?? null,
    username: payload?.user?.username ?? '',
    role: payload?.user?.role ?? '',
    email: payload?.user?.email ?? '',
  }
  authState.isAuthenticated = true

  localStorage.setItem('exam_token', payload.token)
  localStorage.setItem('exam_user', JSON.stringify(payload.user))
}

export function clearAuth() {
  // 退出登录时同时清理内存与本地缓存。
  authState.token = ''
  authState.user = {
    id: null,
    username: '',
    role: '',
    email: '',
  }
  authState.isAuthenticated = false

  localStorage.removeItem('exam_token')
  localStorage.removeItem('exam_user')
}
