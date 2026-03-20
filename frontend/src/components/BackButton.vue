<template>
  <button class="back-btn" @click="goBack">← 返回上一页</button>
</template>

<script setup>
import { useRouter } from 'vue-router'

const router = useRouter()

const goBack = () => {
  if (window.history.length > 1) {
    router.back()
    return
  }
  router.push('/dashboard')
}
</script>

<style scoped>
.back-btn {
  border: 1px solid var(--line);
  background: #fff;
  color: var(--brand-deep);
  border-radius: 999px;
  padding: 0.42rem 0.85rem;
  font-weight: 700;
}
</style>
