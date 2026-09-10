<script setup lang="ts">
import { computed } from 'vue'
import { Dialog, DialogPanel, DialogTitle, TransitionChild, TransitionRoot } from '@headlessui/vue'

const props = defineProps<{
  open: boolean
  isCompetition: boolean
}>()

const emit = defineEmits<{
  close: []
  start: []
}>()

const instructions = computed(() => {
  if (props.isCompetition) {
    return [
      "Read the challenge.",
      "Find the participant who matches the challenge.",
      "Take a selfie together.",
      "Submit your challenge.",
      "Complete challenges quickly to earn Speed Bonus points."
    ]
  }
  return [
    "Read the challenge carefully.",
    "Find a participant who matches the challenge.",
    "Take a selfie together.",
    "Submit the challenge.",
    "Your selfie and achievement will appear on the Public Wall."
  ]
})
</script>

<template>
  <TransitionRoot as="template" :show="open">
    <Dialog as="div" class="relative z-50" @close="emit('close')">
      <TransitionChild
        as="template"
        enter="ease-out duration-300"
        enter-from="opacity-0"
        enter-to="opacity-100"
        leave="ease-in duration-200"
        leave-from="opacity-100"
        leave-to="opacity-0"
      >
        <div class="fixed inset-0 bg-black/80 backdrop-blur-sm transition-opacity" />
      </TransitionChild>

      <div class="fixed inset-0 z-10 w-screen overflow-y-auto">
        <div class="flex min-h-full items-center justify-center p-4 text-center sm:p-0">
          <TransitionChild
            as="template"
            enter="ease-out duration-300"
            enter-from="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95"
            enter-to="opacity-100 translate-y-0 sm:scale-100"
            leave="ease-in duration-200"
            leave-from="opacity-100 translate-y-0 sm:scale-100"
            leave-to="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95"
          >
            <DialogPanel class="relative w-full max-w-sm transform overflow-hidden rounded-2xl bg-[#1e2336] p-6 text-left align-middle shadow-xl transition-all border border-indigo-500/30">
              <div class="flex justify-between items-center mb-4">
                <DialogTitle as="h3" class="text-xl font-bold leading-6 text-white flex items-center gap-2">
                  <span class="text-2xl">🎮</span> How to Play
                </DialogTitle>
                <button
                  type="button"
                  class="text-gray-400 hover:text-white transition-colors"
                  @click="emit('close')"
                  aria-label="Close"
                >
                  <svg class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              <div class="mt-2">
                <p class="text-sm text-indigo-200 mb-4 font-medium uppercase tracking-wider">
                  {{ isCompetition ? 'Competition Mode' : 'Networking Mode' }}
                </p>
                <ol class="space-y-3">
                  <li v-for="(step, i) in instructions" :key="i" class="flex gap-3 text-sm text-gray-300 items-start">
                    <span class="flex items-center justify-center w-6 h-6 rounded-full bg-indigo-600 text-white font-bold text-xs shrink-0 mt-0.5">
                      {{ i + 1 }}
                    </span>
                    <span>{{ step }}</span>
                  </li>
                </ol>
              </div>

              <div class="mt-8 flex flex-col gap-3">
                <button
                  type="button"
                  class="btn-primary w-full py-3 font-semibold text-lg"
                  @click="emit('start')"
                >
                  Got it, let's play!
                </button>
                <button
                  type="button"
                  class="w-full py-2 text-sm text-gray-400 hover:text-white transition-colors"
                  @click="emit('close')"
                >
                  Skip
                </button>
              </div>
            </DialogPanel>
          </TransitionChild>
        </div>
      </div>
    </Dialog>
  </TransitionRoot>
</template>
