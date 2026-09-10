import type { ParticipantTask } from '@/types'
import { isTaskCompleted } from '@/utils/taskStatus'

export const MEET_CHALLENGE_SUMMARY =
  'Meet 3 different people. Take a selfie with each person you connect with.'

export const MEET_PERSON_DESCRIPTION =
  'Meet a different person. Take a selfie with each person you connect with.'

const SCAN_COPY = /scan|badge|qr/i

export function taskTargetCount(task: ParticipantTask): number {
  return task.target_count ?? 1
}

export function taskProgressCount(task: ParticipantTask): number {
  return task.progress_count ?? 0
}

export function taskDescription(task: ParticipantTask): string | null {
  if (task.description && !SCAN_COPY.test(task.description)) {
    return task.description
  }
  if (task.slug?.startsWith('meet-person-')) {
    return MEET_PERSON_DESCRIPTION
  }
  if (task.type === 'scan' || task.type === 'selfie') {
    return MEET_PERSON_DESCRIPTION
  }
  return task.description
}

export function taskGroupLabel(task: ParticipantTask): string | null {
  return task.group_label ?? null
}

export function taskProgressLabel(task: ParticipantTask): string | null {
  const target = task.meet_group_total ?? taskTargetCount(task)
  if (target <= 1) {
    return task.status === 'completed' ? null : null
  }
  const done = taskProgressCount(task)
  if (task.slug?.startsWith('meet-person-')) {
    return task.status === 'completed' ? 'Done' : null
  }
  return `${done} of ${target} people`
}

export type TaskListSection = {
  key: string
  groupLabel: string | null
  tasks: ParticipantTask[]
}

const MEET_PERSON_SLUG_RE = /^meet-person-\d+-of-\d+$/
const MEET_LEGACY_SLUG_RE = /^meet-\d+$/

/** Selfie “meet N people” series (split or legacy single row). */
export function isMeetSeriesTask(task: ParticipantTask): boolean {
  const slug = task.slug ?? ''
  if (MEET_PERSON_SLUG_RE.test(slug) || MEET_LEGACY_SLUG_RE.test(slug)) return true
  if (/^Meet \d+ People$/i.test(task.title)) return true
  return false
}

export function isIntroTask(task: ParticipantTask): boolean {
  return task.slug === 'intro' || task.title === 'Introduction'
}

/** Group meet-person-1-of-3, etc. under one challenge heading. */
export type MeetListSection = {
  key: string
  total: number
  summary: string
  tasks: ParticipantTask[]
  completed: number
}

/** Split meet-person rows by challenge size (e.g. 3-of-3 vs 5-of-5). */
export function buildMeetSections(tasks: ParticipantTask[]): MeetListSection[] {
  const meet = tasks.filter(isMeetSeriesTask)
  if (!meet.length) return []

  const byTotal = new Map<number, ParticipantTask[]>()
  for (const t of meet) {
    const n = t.meet_group_total ?? taskTargetCount(t) ?? 3
    const arr = byTotal.get(n) ?? []
    arr.push(t)
    byTotal.set(n, arr)
  }

  return [...byTotal.entries()]
    .sort((a, b) => a[0] - b[0])
    .map(([total, items]) => {
      const sorted = [...items].sort(
        (a, b) => (a.meet_group_index ?? 0) - (b.meet_group_index ?? 0)
      )
      const summary =
        sorted.find((t) => t.group_label)?.group_label ??
        (total === 3
          ? MEET_CHALLENGE_SUMMARY
          : `Meet ${total} different people. Take a selfie with each person you connect with.`)
      return {
        key: `meet-${total}`,
        total,
        summary,
        tasks: sorted,
        completed: sorted.filter((t) => isTaskCompleted(t.status)).length,
      }
    })
}

export function buildTaskSections(tasks: ParticipantTask[]): TaskListSection[] {
  const meetTasks = tasks.filter(isMeetSeriesTask)
  const meetSlugs = new Set(meetTasks.map((t) => t.slug))
  const other = tasks.filter(
    (t) => !meetSlugs.has(t.slug ?? '') && !isMeetSeriesTask(t) && !isIntroTask(t)
  )

  if (meetTasks.length === 0) {
    const rest = tasks.filter((t) => !isIntroTask(t))
    return rest.length ? [{ key: 'all', groupLabel: null, tasks: rest }] : []
  }

  const total = meetTasks[0]?.meet_group_total ?? 3
  const label =
    meetTasks.find((t) => t.group_label)?.group_label ??
    (total === 3
      ? MEET_CHALLENGE_SUMMARY
      : `Meet ${total} different people. Take a selfie with each person you connect with.`)

  const sections: TaskListSection[] = [
    { key: 'meet-group', groupLabel: label, tasks: meetTasks },
  ]
  if (other.length) {
    sections.push({ key: 'other', groupLabel: null, tasks: other })
  }
  return sections
}
