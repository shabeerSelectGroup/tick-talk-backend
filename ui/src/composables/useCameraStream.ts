import { isCameraSupported, queryCameraPermission } from '@/utils/camera'

/** Fast preview constraints — full quality is applied server-side on upload. */
export const CAMERA_PREVIEW_CONSTRAINTS: MediaStreamConstraints = {
  video: {
    facingMode: 'user',
    width: { ideal: 1280, max: 1920 },
    height: { ideal: 720, max: 1080 },
  },
  audio: false,
}

let warmStream: MediaStream | null = null
let warmPromise: Promise<MediaStream> | null = null

export async function acquireCameraStream(): Promise<MediaStream> {
  if (warmStream?.active) {
    return warmStream
  }
  if (!warmPromise) {
    warmPromise = navigator.mediaDevices
      .getUserMedia(CAMERA_PREVIEW_CONSTRAINTS)
      .then((stream) => {
        warmStream = stream
        warmPromise = null
        return stream
      })
      .catch((err) => {
        warmPromise = null
        throw err
      })
  }
  return warmPromise
}

/** Start camera in the background while the user browses challenges. */
export function prewarmCamera(): void {
  if (!isCameraSupported()) return
  void queryCameraPermission().then((perm) => {
    if (perm === 'granted') {
      void acquireCameraStream().catch(() => undefined)
    }
  })
}

export function releaseCameraStream(): void {
  warmStream?.getTracks().forEach((t) => t.stop())
  warmStream = null
  warmPromise = null
}
