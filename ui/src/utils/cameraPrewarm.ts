import { isCameraSupported, queryCameraPermission } from '@/utils/camera'

/** Fast preview constraints — full photo still captured from this stream. */
export const CAMERA_PREVIEW_CONSTRAINTS: MediaStreamConstraints = {
  video: {
    facingMode: 'user',
    width: { ideal: 640, max: 1280 },
    height: { ideal: 480, max: 720 },
  },
  audio: false,
}

let prewarmedStream: MediaStream | null = null
let prewarmPromise: Promise<MediaStream | null> | null = null
let prewarmVideo: HTMLVideoElement | null = null

function stopStream(stream: MediaStream | null) {
  stream?.getTracks().forEach((t) => t.stop())
}

function ensurePrewarmVideo(): HTMLVideoElement {
  if (!prewarmVideo && typeof document !== 'undefined') {
    const el = document.createElement('video')
    el.muted = true
    el.playsInline = true
    el.setAttribute('playsinline', 'true')
    el.setAttribute('webkit-playsinline', 'true')
    el.setAttribute('aria-hidden', 'true')
    Object.assign(el.style, {
      position: 'fixed',
      width: '1px',
      height: '1px',
      opacity: '0',
      pointerEvents: 'none',
      left: '-9999px',
      top: '0',
    })
    document.body.appendChild(el)
    prewarmVideo = el
  }
  return prewarmVideo!
}

async function waitForVideoDimensions(
  video: HTMLVideoElement,
  maxMs = 400
): Promise<boolean> {
  if (video.videoWidth > 0 && video.videoHeight > 0) return true

  return new Promise((resolve) => {
    const started = performance.now()
    const tick = () => {
      if (video.videoWidth > 0 && video.videoHeight > 0) {
        resolve(true)
        return
      }
      if (performance.now() - started >= maxMs) {
        resolve(video.readyState >= HTMLMediaElement.HAVE_CURRENT_DATA)
        return
      }
      requestAnimationFrame(tick)
    }
    const onReady = () => {
      video.removeEventListener('loadeddata', onReady)
      resolve(video.videoWidth > 0 || video.readyState >= HTMLMediaElement.HAVE_CURRENT_DATA)
    }
    video.addEventListener('loadeddata', onReady, { once: true })
    requestAnimationFrame(tick)
  })
}

async function attachToPrewarmVideo(stream: MediaStream): Promise<void> {
  const video = ensurePrewarmVideo()
  if (video.srcObject !== stream) {
    video.srcObject = stream
  }
  await video.play().catch(() => undefined)
  await waitForVideoDimensions(video)
}

/** Start camera in the background when permission is already granted. */
export async function prewarmCamera(): Promise<void> {
  if (!isCameraSupported()) return
  if (prewarmedStream?.active) {
    await attachToPrewarmVideo(prewarmedStream)
    return
  }
  if (prewarmPromise) {
    await prewarmPromise
    return
  }

  const perm = await queryCameraPermission()
  if (perm !== 'granted') return

  prewarmPromise = navigator.mediaDevices
    .getUserMedia(CAMERA_PREVIEW_CONSTRAINTS)
    .then(async (stream) => {
      stopStream(prewarmedStream)
      prewarmedStream = stream
      await attachToPrewarmVideo(stream)
      return stream
    })
    .catch(() => null)
    .finally(() => {
      prewarmPromise = null
    })

  await prewarmPromise
}

/** True when a prewarmed stream is ready to attach instantly. */
export function hasPrewarmedCamera(): boolean {
  return Boolean(prewarmedStream?.active)
}

/** Hand off prewarmed stream to SelfieCamera (caller owns it after this). */
export function takePrewarmedStream(): MediaStream | null {
  const stream = prewarmedStream
  prewarmedStream = null
  if (prewarmVideo) {
    prewarmVideo.srcObject = null
  }
  return stream?.active ? stream : null
}

/** Keep camera running off-screen for the next selfie modal. */
export function returnStreamToPrewarm(stream: MediaStream | null): void {
  if (!stream?.active) return
  stopStream(prewarmedStream)
  prewarmedStream = stream
  void attachToPrewarmVideo(stream)
}

export function releasePrewarmedStream(): void {
  stopStream(prewarmedStream)
  prewarmedStream = null
  prewarmPromise = null
  if (prewarmVideo) {
    prewarmVideo.srcObject = null
  }
}
