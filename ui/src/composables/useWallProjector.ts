import { onMounted, onUnmounted, ref } from 'vue'

export function useWallProjector() {
  const projectorMode = ref(false)
  const isFullscreen = ref(false)

  function toggleProjector() {
    projectorMode.value = !projectorMode.value
    if (projectorMode.value) {
      void enterFullscreen()
    } else {
      void exitFullscreen()
    }
  }

  async function enterFullscreen() {
    try {
      const el = document.documentElement
      if (el.requestFullscreen) await el.requestFullscreen()
    } catch {
      /* ignore — projector layout still applies */
    }
  }

  async function exitFullscreen() {
    try {
      if (document.fullscreenElement) await document.exitFullscreen()
    } catch {
      /* ignore */
    }
  }

  function onFullscreenChange() {
    isFullscreen.value = Boolean(document.fullscreenElement)
    if (!isFullscreen.value) projectorMode.value = false
  }

  onMounted(() => {
    document.addEventListener('fullscreenchange', onFullscreenChange)
  })

  onUnmounted(() => {
    document.removeEventListener('fullscreenchange', onFullscreenChange)
    if (projectorMode.value) void exitFullscreen()
  })

  return { projectorMode, isFullscreen, toggleProjector }
}
