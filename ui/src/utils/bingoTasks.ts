import { NETWORKING_BINGO_CATALOG } from '@/data/networkingBingoCatalog'
import type { ParticipantTask } from '@/types'
import { isTaskCompleted } from '@/utils/taskStatus'

export const BINGO_CATEGORY_LABELS: Record<string, string> = {
  travel: 'Travel & Personal',
  professional: 'Professional',
  skills: 'Skills',
  fun_facts: 'Fun Facts',
  networking: 'Networking & Leadership',
  ice_breakers: 'Ice Breakers',
}

/** Short labels for compact bingo grid row headers */
export const BINGO_CATEGORY_SHORT: Record<string, string> = {
  travel: 'Travel',
  professional: 'Pro',
  skills: 'Skills',
  fun_facts: 'Fun',
  networking: 'Network',
  ice_breakers: 'Icebreaker',
}

export const BINGO_CATEGORY_ICON: Record<string, string> = {
  travel: '✈️',
  professional: '💼',
  skills: '⚡',
  fun_facts: '🎯',
  networking: '🤝',
  ice_breakers: '☕',
}

/** 30+ distinct emblems — one unique icon per bingo card when possible */
export const BINGO_CARD_EMBLEMS = [
  '✈️', '🌍', '🧳', '🏖️', '🗺️',
  '💼', '📊', '💻', '🏢', '📈',
  '⚡', '🧠', '🎤', '📚', '🔧',
  '🎯', '⚽', '🏏', '🍳', '🎬',
  '🤝', '🌐', '👥', '🚀', '🏆',
  '🎂', '🎨', '☕', '🍵', '🆕',
  '🌟', '🎲', '🎪', '🎵', '💡',
  '🎸', '📷', '🎁', '🌈', '🦋',
  '🍕', '🎳', '🧩', '🔮', '🎭',
] as const

function fisherYatesShuffle<T>(items: T[]): T[] {
  const arr = [...items]
  for (let i = arr.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[arr[i], arr[j]] = [arr[j], arr[i]]
  }
  return arr
}

function hashString(value: string): number {
  let h = 0
  for (let i = 0; i < value.length; i++) {
    h = (h * 31 + value.charCodeAt(i)) >>> 0
  }
  return h
}

/** Stable varied emblem per task (fallback). */
export function randomCardEmblem(task: ParticipantTask): string {
  const key = task.slug ?? String(task.id)
  const h = hashString(key)
  return BINGO_CARD_EMBLEMS[h % BINGO_CARD_EMBLEMS.length]
}

export function taskFlipKey(task: ParticipantTask): string {
  return String(task.slug ?? task.id)
}

export type BingoCardSlot = {
  task: ParticipantTask
  emblem: string
  key: string
  /** Subtle Z rotation for scattered deck look (degrees) */
  tiltZ: number
}

function cardTilt(task: ParticipantTask): number {
  const h = hashString(task.slug ?? String(task.id))
  return (h % 7) - 3
}

function assignUniqueEmblems(tasks: ParticipantTask[]): Map<string, string> {
  const pool = fisherYatesShuffle([...BINGO_CARD_EMBLEMS])
  const map = new Map<string, string>()
  tasks.forEach((task, index) => {
    map.set(taskFlipKey(task), pool[index % pool.length])
  })
  return map
}

/** Flatten sections and shuffle card positions; emblem per task is varied. */
export function buildShuffledBingoCards(sections: BingoSection[]): BingoCardSlot[] {
  const tasks = sections.flatMap((s) => s.tasks)
  const shuffled = fisherYatesShuffle(tasks)
  const emblemMap = assignUniqueEmblems(shuffled)
  return shuffled.map((task) => ({
    task,
    emblem: emblemMap.get(taskFlipKey(task)) ?? randomCardEmblem(task),
    key: taskFlipKey(task),
    tiltZ: cardTilt(task),
  }))
}

/** Re-order slots after refresh while keeping layout stable for known tasks. */
export function mergeShuffledBingoCards(
  previous: BingoCardSlot[],
  sections: BingoSection[]
): BingoCardSlot[] {
  const fresh = buildShuffledBingoCards(sections)
  if (!previous.length) return fresh

  const indexByKey = new Map(previous.map((s, i) => [s.key, i]))
  return [...fresh].sort((a, b) => {
    const ai = indexByKey.get(a.key) ?? 999
    const bi = indexByKey.get(b.key) ?? 999
    return ai - bi
  })
}

export type BingoSection = {
  key: string
  label: string
  tasks: ParticipantTask[]
  completed: number
  total: number
}

export function isBingoTask(task: ParticipantTask): boolean {
  return Boolean(task.bingo || task.slug?.startsWith('bingo-'))
}

export function isBingoEvent(tasks: ParticipantTask[], eventMode?: string | null): boolean {
  if (eventMode === 'networking' || eventMode === 'competition') return true
  return tasks.some(isBingoTask)
}

/** Placeholder rows when server has not synced assignments yet. */
export function catalogAsParticipantTasks(): ParticipantTask[] {
  return NETWORKING_BINGO_CATALOG.map((item, index) => ({
    id: -(index + 1),
    task_id: -(index + 1),
    slug: item.slug,
    bingo: true,
    category: item.category,
    title: item.title,
    description: item.description,
    type: 'selfie',
    status: 'pending',
    points: 0,
    completed_at: null,
  }))
}

export function mergeBingoTasks(apiTasks: ParticipantTask[]): ParticipantTask[] {
  const bingoApi = apiTasks.filter((t) => t.bingo || t.slug?.startsWith('bingo-'))
  const bySlug = new Map(bingoApi.map((t) => [t.slug ?? '', t]))
  if (bySlug.size === 0) {
    return catalogAsParticipantTasks()
  }
  const catalogSlugs = new Set(NETWORKING_BINGO_CATALOG.map((item) => item.slug))
  const catalogTasks = NETWORKING_BINGO_CATALOG.map((item, index) => {
    const existing = bySlug.get(item.slug)
    if (existing) {
      return { ...existing, bingo: true, category: item.category }
    }
    return catalogAsParticipantTasks()[index]
  })
  const extras = bingoApi
    .filter((t) => t.id > 0 && !catalogSlugs.has(t.slug ?? ''))
    .map((t) => ({ ...t, bingo: true, category: t.category ?? 'ice_breakers' }))
  return [...catalogTasks, ...extras]
}

export function buildBingoSections(tasks: ParticipantTask[]): BingoSection[] {
  const bingo = tasks.filter((t) => t.bingo)
  const byCategory = new Map<string, ParticipantTask[]>()

  for (const t of bingo) {
    const cat = t.category ?? 'other'
    if (!byCategory.has(cat)) byCategory.set(cat, [])
    byCategory.get(cat)!.push(t)
  }

  const order = Object.keys(BINGO_CATEGORY_LABELS)
  const sections: BingoSection[] = []

  for (const key of order) {
    const items = byCategory.get(key)
    if (!items?.length) continue
    sections.push({
      key,
      label: BINGO_CATEGORY_LABELS[key] ?? key,
      tasks: items,
      completed: items.filter((t) => isTaskCompleted(t.status)).length,
      total: items.length,
    })
    byCategory.delete(key)
  }

  for (const [key, items] of byCategory) {
    sections.push({
      key,
      label: BINGO_CATEGORY_LABELS[key] ?? key,
      tasks: items,
      completed: items.filter((t) => isTaskCompleted(t.status)).length,
      total: items.length,
    })
  }

  return sections
}
