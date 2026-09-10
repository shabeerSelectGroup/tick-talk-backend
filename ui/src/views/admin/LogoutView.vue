<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAdminAuthStore } from '@/stores/adminAuth'

const router = useRouter()
const adminAuth = useAdminAuthStore()
const message = ref('Signing out…')

onMounted(async () => {
  await adminAuth.logout()
  message.value = 'Signed out'
  router.replace({ name: 'admin-login' })
})
</script>

<template>
  <div class="flex min-h-[40vh] flex-col items-center justify-center game-muted">
    <p>{{ message }}</p>
  </div>
</template>
