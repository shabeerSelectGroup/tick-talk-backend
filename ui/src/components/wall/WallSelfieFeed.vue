<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import type { WallSelfie } from '@/types/wall'
import { resolveMediaUrl } from '@/utils/mediaUrl'
import { selfieDisplayUrl } from '@/utils/selfieMedia'

const props = defineProps<{
  selfies: WallSelfie[]
  large?: boolean
}>()

function selfieSrc(s: WallSelfie): string {
  return selfieDisplayUrl(s)
}

function fullUrl(s: WallSelfie): string {
  return resolveMediaUrl(s.image_url) || selfieSrc(s)
}

const lightboxIndex = ref<number | null>(null)
const currentSelfie = computed(() => 
  lightboxIndex.value !== null ? props.selfies[lightboxIndex.value] : null
)

function openLightbox(index: number) {
  lightboxIndex.value = index
  document.documentElement.style.overflow = 'hidden'
}

function closeLightbox() {
  lightboxIndex.value = null
  document.documentElement.style.overflow = ''
}

function nextPhoto(e?: Event) {
  e?.stopPropagation()
  if (lightboxIndex.value === null) return
  if (lightboxIndex.value < props.selfies.length - 1) {
    lightboxIndex.value++
  }
}

function prevPhoto(e?: Event) {
  e?.stopPropagation()
  if (lightboxIndex.value === null) return
  if (lightboxIndex.value > 0) {
    lightboxIndex.value--
  }
}

function onKeydown(e: KeyboardEvent) {
  if (lightboxIndex.value === null) return
  if (e.key === 'ArrowRight') nextPhoto()
  if (e.key === 'ArrowLeft') prevPhoto()
  if (e.key === 'Escape') closeLightbox()
}

onMounted(() => {
  window.addEventListener('keydown', onKeydown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', onKeydown)
  document.documentElement.style.overflow = ''
})

let touchStartX = 0
let touchEndX = 0

function onTouchStart(e: TouchEvent) {
  touchStartX = e.changedTouches[0].screenX
}

function onTouchEnd(e: TouchEvent) {
  touchEndX = e.changedTouches[0].screenX
  handleSwipe()
}

function handleSwipe() {
  const diff = touchStartX - touchEndX
  if (diff > 50) nextPhoto()
  if (diff < -50) prevPhoto()
}
</script>

<template>
  <div
    class="grid gap-3 tt-stagger"
    :class="
      large
        ? 'grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5'
        : 'grid-cols-2 sm:grid-cols-3 md:grid-cols-4'
    "
  >
    <article
      v-for="(s, i) in selfies"
      :key="s.id"
      class="game-wall-selfie tt-selfie-new group relative aspect-square cursor-pointer overflow-hidden"
      @click="openLightbox(i)"
    >
      <img
        :src="selfieSrc(s)"
        :alt="`${s.display_name}${s.task_title ? ` — ${s.task_title}` : ''}`"
        class="h-full w-full object-cover transition duration-500 group-hover:scale-105"
        loading="lazy"
        decoding="async"
      />
      <div class="game-wall-selfie__caption absolute inset-x-0 bottom-0 px-3 pb-3 pt-10">
        <p
          v-if="s.task_title"
          class="mb-0.5 truncate text-[10px] font-bold uppercase tracking-wide text-amber-300/90"
        >
          {{ s.task_title }}
        </p>
        <p class="truncate font-bold text-amber-50" :class="large ? 'text-lg' : 'text-sm'">
          {{ s.display_name }}
        </p>
        <p v-if="s.partner_name" class="truncate text-xs text-amber-100/80">
          with {{ s.partner_name }}
        </p>
        <p v-if="s.company" class="truncate text-xs text-amber-100/60">{{ s.company }}</p>
      </div>
    </article>
    <p v-if="!selfies.length" class="game-empty-state col-span-full py-16 text-center">
      Selfies will appear here as participants upload them
    </p>

    <!-- Lightbox -->
    <Teleport to="body">
      <Transition name="tt-page">
        <div
          v-if="currentSelfie && lightboxIndex !== null"
          class="fixed inset-0 z-[200] flex flex-col bg-black/95 backdrop-blur-xl touch-none"
          @click="closeLightbox"
          @touchstart="onTouchStart"
          @touchend="onTouchEnd"
        >
          <!-- Top bar -->
          <div class="flex items-center justify-end p-4 z-10 bg-gradient-to-b from-black/50 to-transparent">
            <button
              type="button"
              class="flex h-10 w-10 items-center justify-center rounded-full bg-white/10 text-white hover:bg-white/20 transition"
              @click.stop="closeLightbox"
            >
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="h-6 w-6"><path d="M18 6L6 18M6 6l12 12"></path></svg>
            </button>
          </div>

          <!-- Main Image Area -->
          <div class="relative flex-1 flex items-center justify-center overflow-hidden">
            <!-- Prev Button -->
            <button
              v-if="lightboxIndex > 0"
              class="absolute left-2 top-1/2 -translate-y-1/2 z-10 flex h-12 w-12 items-center justify-center rounded-full bg-black/50 text-white backdrop-blur hover:bg-black/80 transition hidden sm:flex"
              @click.stop="prevPhoto"
            >
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="h-6 w-6"><path d="M15 18l-6-6 6-6"></path></svg>
            </button>

            <!-- Image -->
            <img
              :key="currentSelfie.id"
              :src="fullUrl(currentSelfie)"
              class="max-h-full max-w-full object-contain"
              @click.stop
            />

            <!-- Info Overlay -->
            <div class="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/80 to-transparent pt-20 pb-8 px-6 pointer-events-none flex flex-col items-center text-center">
              <div class="text-white">
                <p class="font-bold text-2xl md:text-4xl drop-shadow-lg">{{ currentSelfie.display_name }}</p>
                <p v-if="currentSelfie.partner_name" class="text-base md:text-xl text-white/80 mt-1 drop-shadow-md">
                  with {{ currentSelfie.partner_name }}
                </p>
                <p v-if="currentSelfie.task_title" class="text-lg md:text-2xl text-white/90 mt-2 drop-shadow-md max-w-3xl">{{ currentSelfie.task_title }}</p>
              </div>
            </div>

            <!-- Next Button -->
            <button
              v-if="lightboxIndex < selfies.length - 1"
              class="absolute right-2 top-1/2 -translate-y-1/2 z-10 flex h-12 w-12 items-center justify-center rounded-full bg-black/50 text-white backdrop-blur hover:bg-black/80 transition hidden sm:flex"
              @click.stop="nextPhoto"
            >
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="h-6 w-6"><path d="M9 18l6-6-6-6"></path></svg>
            </button>
          </div>

          <!-- Bottom Counter -->
          <div class="p-4 text-center text-sm font-medium text-white/50">
            {{ lightboxIndex + 1 }} of {{ selfies.length }}
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>
