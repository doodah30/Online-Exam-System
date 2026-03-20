import axios from 'axios'

// 前端所有接口都通过这个实例访问后端。
const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api'

export const api = axios.create({
  baseURL: BASE_URL,
})

api.interceptors.request.use((config) => {
  // 若本地保存了 token，则自动放到 Authorization 请求头。
  // 后端会用 TokenAuthentication 校验该 token。
  const token = localStorage.getItem('exam_token')
  if (token) {
    config.headers.Authorization = `Token ${token}`
  }
  return config
})
