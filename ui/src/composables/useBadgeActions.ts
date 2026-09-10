import { ref } from 'vue'
import { useBadgeStore } from '@/stores/badge'
import type { ParticipantBadge } from '@/types/badge'

export function useBadgeActions(getBadge: () => ParticipantBadge | null) {
  const busy = ref(false)
  const actionMessage = ref('')
  const badgeStore = useBadgeStore()

  async function downloadBadge() {
    busy.value = true
    actionMessage.value = ''
    try {
      const blob = await badgeStore.downloadBadgePng()
      const b = getBadge()
      const name = b
        ? `ticktalk-badge-${b.event_code}-${b.participant_id}.png`
        : 'ticktalk-badge.png'
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = name
      link.click()
      URL.revokeObjectURL(url)
      actionMessage.value = 'Badge downloaded'
    } catch {
      const b = getBadge()
      if (b?.qr_code_data_url) {
        const link = document.createElement('a')
        link.href = b.qr_code_data_url
        link.download = `ticktalk-badge-${b.event_code}-${b.participant_id}.png`
        link.click()
        actionMessage.value = 'Badge downloaded'
      } else {
        actionMessage.value = 'Could not download badge'
      }
    } finally {
      busy.value = false
    }
  }

  async function shareBadge() {
    const b = getBadge()
    if (!b) return
    busy.value = true
    actionMessage.value = ''
    try {
      const shareData: ShareData = {
        title: `${b.display_name} — Tick Talk`,
        text: `${b.display_name} is at event ${b.event_code} (participant #${b.participant_id}).`,
      }
      if (navigator.share) {
        try {
          const blob = await badgeStore.downloadBadgePng()
          const file = new File([blob], `badge-${b.participant_id}.png`, { type: 'image/png' })
          if (navigator.canShare?.({ files: [file] })) {
            await navigator.share({ ...shareData, files: [file] })
            actionMessage.value = 'Shared'
            return
          }
        } catch {
          /* fall through to text-only share */
        }
        await navigator.share(shareData)
        actionMessage.value = 'Shared'
      } else if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(shareData.text ?? b.display_name)
        actionMessage.value = 'Copied to clipboard'
      } else {
        actionMessage.value = 'Sharing not supported on this device'
      }
    } catch (e) {
      if ((e as Error).name !== 'AbortError') {
        actionMessage.value = 'Share cancelled or failed'
      }
    } finally {
      busy.value = false
    }
  }

  return { busy, actionMessage, downloadBadge, shareBadge }
}
