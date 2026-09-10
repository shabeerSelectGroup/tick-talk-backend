<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAdminAuthStore } from '@/stores/adminAuth'

const adminAuth = useAdminAuthStore()
const router = useRouter()
const route = useRoute()

const securityCode = ref('')
const error = ref('')
const loading = ref(false)

const redirectTo = computed(
  () => (route.query.redirect as string) || '/admin/dashboard'
)

async function submit() {
  const code = securityCode.value.trim()
  if (!code) {
    error.value = 'Enter the admin security code'
    return
  }
  loading.value = true
  error.value = ''
  try {
    await adminAuth.loginWithSecurityCode(code)
    router.replace(redirectTo.value)
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Invalid security code'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="w-full max-w-md">
    <div class="admin-panel">
      <div class="admin-panel-body space-y-6">
        <div class="text-center">
          <img src="/icons/icon-192.png" alt="" class="mx-auto h-16 w-16 rounded-2xl" />
          <h1 class="admin-page-title mt-4">TickTalk Admin</h1>
          <p class="admin-muted mt-1">Sign in with your security code</p>
        </div>

        <form class="space-y-4" @submit.prevent="submit">
          <div>
            <label for="security-code" class="admin-label">Security code</label>
            <input
              id="security-code"
              v-model="securityCode"
              type="password"
              autocomplete="off"
              autocapitalize="characters"
              spellcheck="false"
              class="admin-input font-mono tracking-wide"
              placeholder="Enter admin code"
              required
            />
          </div>

          <p v-if="error" class="admin-alert admin-alert--error" role="alert">{{ error }}</p>

          <button type="submit" class="admin-btn-primary w-full" :disabled="loading">
            {{ loading ? 'Signing in…' : 'Sign in' }}
          </button>
        </form>
      </div>
    </div>
  </div>
</template>
