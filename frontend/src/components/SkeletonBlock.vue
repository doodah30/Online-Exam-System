<template>
  <div class="skeleton-list">
    <div v-for="idx in rows" :key="idx" class="skeleton-row card">
      <div class="skeleton h-title"></div>
      <div class="skeleton h-line"></div>
      <div class="skeleton h-line w-70"></div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  rows: {
    type: Number,
    default: 3,
  },
})
</script>

<style scoped>
.skeleton-list {
  display: grid;
  gap: 0.7rem;
}

.skeleton-row {
  display: grid;
  gap: 0.55rem;
}

.h-title {
  height: 16px;
}

.h-line {
  height: 12px;
}

.w-70 {
  width: 70%;
}
</style>
