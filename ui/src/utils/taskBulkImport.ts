/** Parse uploaded .txt / .csv into bulk-import text (one task per line, optional | description). */

const MAX_FILE_BYTES = 512 * 1024

export function csvRowToLine(row: string[]): string | null {
  const title = (row[0] ?? '').trim()
  if (!title || title.startsWith('#')) return null
  const desc = (row[1] ?? '').trim()
  return desc ? `${title}|${desc}` : title
}

/** Minimal CSV parse: handles quoted fields and commas. */
export function parseCsvContent(raw: string): string {
  const lines: string[] = []
  const rows = raw.replace(/\r\n/g, '\n').replace(/\r/g, '\n').split('\n')
  let start = 0
  if (rows.length && /^title\s*,/i.test(rows[0])) {
    start = 1
  }
  for (let i = start; i < rows.length; i++) {
    const row = parseCsvLine(rows[i])
    if (!row.length) continue
    const line = csvRowToLine(row)
    if (line) lines.push(line)
  }
  return lines.join('\n')
}

function parseCsvLine(line: string): string[] {
  const out: string[] = []
  let cur = ''
  let inQuotes = false
  for (let i = 0; i < line.length; i++) {
    const ch = line[i]
    if (ch === '"') {
      if (inQuotes && line[i + 1] === '"') {
        cur += '"'
        i++
      } else {
        inQuotes = !inQuotes
      }
    } else if (ch === ',' && !inQuotes) {
      out.push(cur)
      cur = ''
    } else {
      cur += ch
    }
  }
  out.push(cur)
  return out
}

export function fileToBulkImportText(file: File): Promise<string> {
  if (file.size > MAX_FILE_BYTES) {
    return Promise.reject(new Error('File is too large (max 512 KB).'))
  }
  const name = file.name.toLowerCase()
  if (!name.endsWith('.txt') && !name.endsWith('.csv')) {
    return Promise.reject(new Error('Use a .txt or .csv file.'))
  }
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => {
      const raw = String(reader.result ?? '')
      if (name.endsWith('.csv')) {
        resolve(parseCsvContent(raw))
      } else {
        resolve(raw)
      }
    }
    reader.onerror = () => reject(new Error('Could not read file.'))
    reader.readAsText(file)
  })
}

export const TASK_BULK_CSV_TEMPLATE = `title,description
Find someone who works in HR,
Find someone who speaks 3 languages,Ask what languages they speak
Find someone who travelled abroad,
`

export function downloadTaskBulkTemplate() {
  const blob = new Blob([TASK_BULK_CSV_TEMPLATE], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'ticktalk-tasks-template.csv'
  a.click()
  URL.revokeObjectURL(url)
}

export function countImportLines(text: string): number {
  return text
    .split('\n')
    .map((l) => l.trim())
    .filter((l) => l && !l.startsWith('#')).length
}
