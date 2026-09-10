/** Map getUserMedia failures to participant-friendly copy. */
export function cameraErrorMessage(error: unknown): string {
  if (error instanceof DOMException) {
    switch (error.name) {
      case 'NotAllowedError':
      case 'PermissionDeniedError':
        return 'Camera access was blocked. Allow the camera in your browser settings, or upload a photo below.'
      case 'NotFoundError':
      case 'DevicesNotFoundError':
        return 'No camera found on this device. Upload a photo from your gallery instead.'
      case 'NotReadableError':
      case 'TrackStartError':
        return 'Camera is in use by another app. Close other apps and try again, or upload from gallery.'
      case 'OverconstrainedError':
        return 'Camera settings are not supported. Try again or upload from gallery.'
      case 'SecurityError':
        return 'Camera needs a secure connection. Open the app via https:// or http://localhost, not a plain IP address.'
      case 'AbortError':
        return 'Camera was interrupted. Tap Try again or upload from gallery.'
      default:
        break
    }
    if (/permission/i.test(error.message)) {
      return 'Camera access was blocked. Allow the camera in your browser settings, or upload a photo below.'
    }
  }
  if (error instanceof Error) {
    if (/secure|https|localhost/i.test(error.message)) {
      return 'Camera needs a secure connection (https). Upload a photo below if you cannot enable the camera.'
    }
    if (/permission/i.test(error.message)) {
      return 'Camera access was blocked. Allow the camera in your browser settings, or upload a photo below.'
    }
    return error.message
  }
  return 'Camera not available. Upload a photo from your gallery instead.'
}

export function isCameraSupported(): boolean {
  return (
    typeof navigator !== 'undefined' &&
    !!navigator.mediaDevices?.getUserMedia &&
    (typeof window === 'undefined' || window.isSecureContext)
  )
}

export type CameraPermissionState = 'granted' | 'denied' | 'prompt' | 'unsupported'

/** Best-effort read of camera permission (Safari may return 'prompt' until first request). */
export async function queryCameraPermission(): Promise<CameraPermissionState> {
  if (!isCameraSupported()) return 'unsupported'
  try {
    const result = await navigator.permissions.query({ name: 'camera' as PermissionName })
    if (result.state === 'granted') return 'granted'
    if (result.state === 'denied') return 'denied'
    return 'prompt'
  } catch {
    return 'prompt'
  }
}
