<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import QRCode from 'qrcode'

const props = withDefaults(
  defineProps<{ payload: string; size?: number; variant?: 'default' | 'gold' }>(),
  { variant: 'gold' }
)

const canvasRef = ref<HTMLCanvasElement | null>(null)

const QR_COLORS = {
  gold: { dark: '#ff4757', light: '#ffffff' },
  default: { dark: '#ff4757', light: '#ffffff' },
} as const

async function render() {
  if (!canvasRef.value || !props.payload) return
  const colors = QR_COLORS[props.variant]
  await QRCode.toCanvas(canvasRef.value, props.payload, {
    width: props.size ?? 200,
    margin: 2,
    color: colors,
  })
}

onMounted(render)
watch(() => [props.payload, props.variant, props.size], render)
</script>

<template>
  <canvas ref="canvasRef" class="game-qr-canvas mx-auto rounded-lg" />
</template>
