<template>
  <div class="app-shell">
    <header class="topbar">
      <div class="brand" @click="goDashboard">
        <span class="brand-dot"></span>
        <div>
          <h1>Online Exam Studio</h1>
          <p>Vue + Django 在线考试系统</p>
        </div>
      </div>

      <nav class="top-actions">
        <button v-if="!auth.isAuthenticated" class="ghost" @click="goAuth">登录 / 注册</button>
        <div v-else class="user-box">
          <span>{{ auth.user.username }} · {{ roleText }}</span>
          <button class="danger" @click="logout">退出登录</button>
        </div>
      </nav>
    </header>

    <main class="page-wrap">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { authState, clearAuth } from './stores/auth'

const router = useRouter()
const auth = authState

const roleText = computed(() => (auth.user.role === 'teacher' ? '老师' : '学生'))

const goAuth = () => {
  router.push('/auth')
}

const goDashboard = () => {
  if (auth.isAuthenticated) {
    if (auth.user.role === 'teacher') {
      router.push('/teacher')
      return
    }
    router.push('/dashboard')
    return
  }
  router.push('/')
}

const logout = () => {
  clearAuth()
  router.push('/auth')
}
</script>

<style scoped>
.app-shell {
  min-height: 100vh;
}

.topbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem clamp(1rem, 3vw, 2.5rem);
  border-bottom: 1px solid var(--line);
  backdrop-filter: blur(8px);
  position: sticky;
  top: 0;
  z-index: 10;
  background: color-mix(in srgb, var(--bg-2) 84%, white 16%);
}

.brand {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  cursor: pointer;
}

.brand-dot {
  width: 14px;
  height: 14px;
  border-radius: 999px;
  background: linear-gradient(135deg, var(--brand), var(--brand-2));
  box-shadow: 0 0 0 8px color-mix(in srgb, var(--brand) 18%, transparent);
}

.brand h1 {
  font-size: 1.05rem;
  font-weight: 700;
  letter-spacing: 0.2px;
}

.brand p {
  font-size: 0.75rem;
  color: var(--muted);
}

.top-actions {
  display: flex;
  align-items: center;
}

.user-box {
  display: flex;
  align-items: center;
  gap: 0.65rem;
}

.user-box span {
  font-size: 0.9rem;
  color: var(--muted);
}

.page-wrap {
  width: min(1120px, calc(100% - 2rem));
  margin: 2rem auto 3rem;
  animation: rise 0.55s ease;
}

.ghost,
.danger {
  border: 1px solid var(--line);
  background: white;
  border-radius: 999px;
  padding: 0.45rem 0.9rem;
  cursor: pointer;
  font-weight: 600;
}

.danger {
  background: var(--danger-soft);
  border-color: var(--danger-line);
  color: var(--danger);
}

@keyframes rise {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (max-width: 720px) {
  .topbar {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.8rem;
  }

  .page-wrap {
    width: min(1120px, calc(100% - 1rem));
    margin-top: 1rem;
  }
}
</style>