/** Normalize API task status for UI counts and checkmarks. */
export function isTaskCompleted(status: string | undefined | null): boolean {
  return (status ?? '').toLowerCase() === 'completed'
}

export function countCompletedTasks<T extends { status: string }>(tasks: T[]): number {
  return tasks.filter((t) => isTaskCompleted(t.status)).length
}
