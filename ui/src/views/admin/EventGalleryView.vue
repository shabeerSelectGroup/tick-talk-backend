<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { api, unwrap } from '@/api/client'
import AdminPageHeader from '@/components/admin/AdminPageHeader.vue'
import { getErrorMessage } from '@/utils/errors'
import { selfieDisplayUrl } from '@/utils/selfieMedia'

const route = useRoute()
const eventId = computed(() => Number(route.params.id))

interface GallerySelfie {
  id: number
  image_url: string
  thumbnail_url: string
  status: string
  participant_id: number
  partner_name?: string | null
  partner_sign?: string | null
}

const selfies = ref<GallerySelfie[]>([])
const loading = ref(true)
const error = ref('')
const brokenIds = ref<Set<number>>(new Set())

function mediaSrc(s: GallerySelfie) {
  return selfieDisplayUrl(s)
}

function onImgError(id: number) {
  brokenIds.value = new Set(brokenIds.value).add(id)
}

onMounted(async () => {
  loading.value = true
  error.value = ''
  try {
    selfies.value = await unwrap(await api.get(`/admin/events/${eventId.value}/gallery`))
  } catch (e) {
    error.value = getErrorMessage(e)
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div>
    <AdminPageHeader title="Selfie gallery" subtitle="All selfies uploaded for this event." />

    <p v-if="loading" class="admin-muted">Loading gallery…</p>
    <p v-else-if="error" class="admin-alert admin-alert--error" role="alert">{{ error }}</p>

    <div v-else-if="!selfies.length" class="admin-panel">
      <p class="admin-empty">No selfies uploaded yet.</p>
    </div>

    <div v-else class="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
      <article v-for="s in selfies" :key="s.id" class="admin-panel overflow-hidden !p-0">
        <a :href="mediaSrc(s)" target="_blank" rel="noopener noreferrer" class="block aspect-square">
          <img
            v-if="!brokenIds.has(s.id)"
            :src="mediaSrc(s)"
            :alt="`Selfie ${s.id}`"
            class="h-full w-full object-cover"
            loading="lazy"
            @error="onImgError(s.id)"
          />
          <div
            v-else
            class="flex h-full w-full items-center justify-center bg-slate-100 text-xs text-slate-400"
          >
            Image unavailable
          </div>
        </a>
        <div class="border-t border-slate-100 px-3 py-2 text-xs text-slate-500">
          <span class="capitalize">{{ s.status }}</span>
          <span v-if="s.partner_name" class="mt-0.5 block truncate normal-case font-medium text-slate-700">
            with {{ s.partner_name }}
          </span>
        </div>
      </article>
    </div>
  </div>
</template>
