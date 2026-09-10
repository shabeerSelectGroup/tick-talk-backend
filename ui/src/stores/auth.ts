import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { setSessionToken } from '@/api/client'

const SESSION_TOKEN_KEY = 'ticktalk_session_token'
const SESSION_EVENT_CODE_KEY = 'ticktalk_event_code'
const SESSION_PARTICIPANT_ID_KEY = 'ticktalk_participant_id'

/** Participant session — persisted in localStorage for PWA return visits. */
export const useAuthStore = defineStore('auth', () => {
  const sessionToken = ref<string | null>(localStorage.getItem(SESSION_TOKEN_KEY))
  const eventCode = ref<string | null>(localStorage.getItem(SESSION_EVENT_CODE_KEY))
  const participantId = ref<number | null>(
    localStorage.getItem(SESSION_PARTICIPANT_ID_KEY)
      ? Number(localStorage.getItem(SESSION_PARTICIPANT_ID_KEY))
      : null
  )

  const isParticipant = computed(() => !!sessionToken.value)

  function init() {
    setSessionToken(sessionToken.value)
  }

  function setSession(token: string, code: string, pid: number) {
    sessionToken.value = token
    eventCode.value = code.toUpperCase()
    participantId.value = pid
    localStorage.setItem(SESSION_TOKEN_KEY, token)
    localStorage.setItem(SESSION_EVENT_CODE_KEY, code.toUpperCase())
    localStorage.setItem(SESSION_PARTICIPANT_ID_KEY, String(pid))
    setSessionToken(token)
  }

  function clearSession() {
    sessionToken.value = null
    eventCode.value = null
    participantId.value = null
    localStorage.removeItem(SESSION_TOKEN_KEY)
    localStorage.removeItem(SESSION_EVENT_CODE_KEY)
    localStorage.removeItem(SESSION_PARTICIPANT_ID_KEY)
    setSessionToken(null)
  }

  function isSessionForEvent(code: string) {
    return eventCode.value?.toUpperCase() === code.toUpperCase()
  }

  init()
  return {
    sessionToken,
    eventCode,
    participantId,
    isParticipant,
    setSession,
    clearSession,
    isSessionForEvent,
  }
})
