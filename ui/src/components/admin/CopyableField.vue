<script setup lang="ts">
import { ref } from 'vue'
import CopyIconButton from '@/components/admin/CopyIconButton.vue'
import { copyTextToClipboard } from '@/utils/clipboard'

const props = defineProps<{
  text: string
  label: string
  mono?: boolean
  large?: boolean
}>()

const emit = defineEmits<{ error: [] }>()

const copied = ref(false)
let resetTimer: ReturnType<typeof setTimeout> | null = null

async function copy() {
  if (!props.text.trim()) return
  const ok = await copyTextToClipboard(props.text)
  if (!ok) {
    emit('error')
    return
  }
  copied.value = true
  if (resetTimer) clearTimeout(resetTimer)
  resetTimer = setTimeout(() => {
    copied.value = false
    resetTimer = null
  }, 2000)
}
</script>

<template>
  <div class="mt-1 flex items-center gap-2" :class="large ? '' : 'items-start'">
    <button
      type="button"
      class="admin-copy-field min-w-0 flex-1 px-3 py-2 text-left transition active:scale-[0.99]"
      :class="
        mono
          ? large
            ? 'font-mono text-xl font-black tracking-wider'
            : 'break-all font-mono text-sm font-semibold'
          : 'break-all text-sm font-semibold'
      "
      :title="`Click to copy: ${text}`"
      @click="copy"
    >
      {{ text }}
    </button>
    <CopyIconButton :copied="copied" :label="label" @click="copy" />
  </div>
</template>
