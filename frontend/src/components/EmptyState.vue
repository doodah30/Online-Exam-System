<template>
  <div class="empty-wrap">
    <svg class="empty-icon" viewBox="0 0 120 120" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
      <rect x="15" y="22" width="90" height="74" rx="10" fill="#EFF6FF" />
      <rect x="28" y="38" width="64" height="8" rx="4" fill="#BFDBFE" />
      <rect x="28" y="54" width="48" height="8" rx="4" fill="#DBEAFE" />
      <circle cx="84" cy="78" r="12" fill="#2563EB" opacity="0.18" />
      <path d="M82 78H86" stroke="#1D4ED8" stroke-width="2.2" stroke-linecap="round" />
      <path d="M84 76V80" stroke="#1D4ED8" stroke-width="2.2" stroke-linecap="round" />
    </svg>

    <h4>{{ title }}</h4>
    <p class="muted">{{ description }}</p>

    <button v-if="showAction" class="primary" type="button" @click="$emit('action')">
      {{ actionText }}
    </button>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  title: {
    type: String,
    default: '暂无数据',
  },
  description: {
    type: String,
    default: '当前没有可展示的内容。',
  },
  actionText: {
    type: String,
    default: '',
  },
})

defineEmits(['action'])

const showAction = computed(() => Boolean(props.actionText))
</script>

<style scoped>
.empty-wrap {
  min-height: 220px;
  display: grid;
  place-content: center;
  justify-items: center;
  gap: 0.5rem;
  text-align: center;
  padding: 1rem;
}

.empty-icon {
  width: 84px;
  height: 84px;
}

h4 {
  font-size: 1rem;
}

p {
  max-width: 32ch;
}
</style>
