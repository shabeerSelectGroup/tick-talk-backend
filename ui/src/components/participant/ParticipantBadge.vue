<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import QrDisplay from '@/components/QrDisplay.vue'
import { useBadgeActions } from '@/composables/useBadgeActions'
import { useBadgeStore } from '@/stores/badge'
import type { ParticipantBadge } from '@/types/badge'

const props = withDefaults(
  defineProps<{
    /** Inline badge data (e.g. right after join). */
    badge?: ParticipantBadge | null
    /** Fetch from API when no inline badge. */
    autoFetch?: boolean
    compact?: boolean
    showActions?: boolean
    showPayload?: boolean
  }>(),
  {
    badge: null,
    autoFetch: true,
    compact: false,
    showActions: true,
    showPayload: false,
  }
)

const badgeStore = useBadgeStore()
const loading = ref(false)

const resolved = computed(() => props.badge ?? badgeStore.badge)

const { busy, actionMessage, downloadBadge, shareBadge } = useBadgeActions(() => resolved.value)

async function ensureLoaded() {
  if (props.badge || !props.autoFetch) return
  loading.value = true
  try {
    await badgeStore.fetchBadge()
  } finally {
    loading.value = false
  }
}

onMounted(ensureLoaded)
watch(() => props.badge, () => {
  if (!props.badge && props.autoFetch) ensureLoaded()
})

</script>

<template>
  <div
    class="participant-badge w-full"
    :class="compact ? 'text-center' : 'card mx-auto max-w-sm text-center'"
  >
    <div v-if="loading && !resolved" class="flex justify-center py-8">
      <div class="game-spinner h-10 w-10 animate-spin rounded-full border-2 border-t-transparent" />
    </div>

    <template v-else-if="resolved">
      <p class="text-xs font-bold uppercase tracking-wider text-amber-800">Networking badge</p>
      <h2 class="mt-1 text-xl font-black leading-tight" :class="compact ? 'text-lg' : ''">
        {{ resolved.display_name }}
      </h2>
      <p class="game-stat-label mt-1">
        Participant <span class="game-stat font-mono text-base">#{{ resolved.participant_id }}</span>
        <span v-if="resolved.event_code"> · {{ resolved.event_code }}</span>
      </p>
      <p v-if="resolved.company" class="game-stat-label mt-0.5">{{ resolved.company }}</p>

      <div class="relative mx-auto mt-4 inline-block">
        <img
          v-if="resolved.qr_code_data_url"
          :src="resolved.qr_code_data_url"
          :alt="`QR badge for ${resolved.display_name}`"
          class="rounded-xl bg-slate-900"
          :class="compact ? 'h-40 w-40' : 'h-52 w-52'"
        />
        <QrDisplay
          v-else-if="resolved.qr_payload"
          :payload="resolved.qr_payload"
          :size="compact ? 160 : 208"
        />
      </div>

      <p v-if="showPayload" class="game-stat-label mt-3 break-all font-mono text-xs">
        {{ resolved.qr_payload }}
      </p>
      <p v-else class="game-stat-label mt-2 text-xs">Your event badge · {{ resolved.event_code }}</p>

      <div v-if="showActions" class="mt-4 flex flex-wrap justify-center gap-2">
        <button
          type="button"
          class="btn-secondary min-h-10 px-4 text-sm"
          :disabled="busy"
          @click="downloadBadge"
        >
          Download
        </button>
        <button
          type="button"
          class="btn-secondary min-h-10 px-4 text-sm"
          :disabled="busy"
          @click="shareBadge"
        >
          Share
        </button>
      </div>
      <p v-if="actionMessage" class="mt-2 text-xs font-bold text-amber-800">{{ actionMessage }}</p>
    </template>

    <p v-else class="game-stat-label py-6 text-sm">Badge unavailable</p>
  </div>
</template>
