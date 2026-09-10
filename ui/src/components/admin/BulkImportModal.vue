<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import {
  countImportLines,
  downloadTaskBulkTemplate,
  fileToBulkImportText,
} from '@/utils/taskBulkImport'

const props = defineProps<{ open: boolean }>()
const emit = defineEmits<{
  close: []
  import: [text: string]
}>()

const text = ref(`Find someone who works in HR
Find someone who speaks 3 languages
Find someone who travelled abroad
Find someone who plays a musical instrument`)

const tab = ref<'upload' | 'paste'>('upload')
const fileName = ref('')
const fileError = ref('')
const dragging = ref(false)

const example = `# One task per line. Optional description after |
Find someone who works in HR
Find someone who speaks 3 languages|Ask what languages they speak
Find someone who travelled abroad`

const lineCount = computed(() => countImportLines(text.value))

watch(
  () => props.open,
  (open) => {
    if (!open) return
    fileError.value = ''
    fileName.value = ''
    tab.value = 'upload'
  }
)

function useExample() {
  text.value = example
  tab.value = 'paste'
}

async function applyFile(file: File) {
  fileError.value = ''
  try {
    text.value = await fileToBulkImportText(file)
    fileName.value = file.name
    tab.value = 'paste'
  } catch (e) {
    fileError.value = e instanceof Error ? e.message : 'Could not read file'
  }
}

function onFileInput(ev: Event) {
  const input = ev.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (file) void applyFile(file)
}

function onDrop(ev: DragEvent) {
  dragging.value = false
  const file = ev.dataTransfer?.files?.[0]
  if (file) void applyFile(file)
}

function submit() {
  if (lineCount.value === 0) {
    fileError.value = 'Add at least one task (upload a file or paste text).'
    return
  }
  emit('import', text.value)
}
</script>

<template>
  <Teleport to="body">
    <div v-if="open" class="admin-shell">
      <div class="admin-modal-backdrop" @click.self="emit('close')">
        <div class="admin-modal max-h-[90vh] max-w-lg overflow-y-auto p-5 space-y-4" role="dialog">
          <div>
            <h2 class="text-lg font-bold">Bulk upload tasks</h2>
            <p class="admin-muted mt-1 text-sm">
              Import many tasks at once from a file or pasted list. Task order in the file is
              preserved. Existing titles are matched and moved into that order; new lines are
              appended after tasks not in the file.
            </p>
          </div>

          <div class="flex gap-1 rounded-lg border border-slate-200 bg-slate-50 p-1">
            <button
              type="button"
              class="flex-1 rounded-md px-3 py-2 text-sm font-semibold transition"
              :class="tab === 'upload' ? 'bg-white text-indigo-600 shadow-sm' : 'text-slate-600'"
              @click="tab = 'upload'"
            >
              Upload file
            </button>
            <button
              type="button"
              class="flex-1 rounded-md px-3 py-2 text-sm font-semibold transition"
              :class="tab === 'paste' ? 'bg-white text-indigo-600 shadow-sm' : 'text-slate-600'"
              @click="tab = 'paste'"
            >
              Paste text
            </button>
          </div>

          <div v-if="tab === 'upload'" class="space-y-3">
            <div
              class="rounded-xl border-2 border-dashed px-4 py-8 text-center transition"
              :class="dragging ? 'border-indigo-400 bg-indigo-50' : 'border-slate-200 bg-slate-50'"
              @dragover.prevent="dragging = true"
              @dragleave.prevent="dragging = false"
              @drop.prevent="onDrop"
            >
              <p class="font-semibold text-slate-700">Drop a .txt or .csv file here</p>
              <p class="admin-muted mt-1 text-sm">or choose a file from your computer</p>
              <label class="admin-btn-primary mt-4 inline-flex cursor-pointer">
                Choose file
                <input
                  type="file"
                  accept=".txt,.csv,text/plain,text/csv"
                  class="sr-only"
                  @change="onFileInput"
                />
              </label>
            </div>
            <p v-if="fileName" class="text-sm text-emerald-700">
              Loaded <span class="font-semibold">{{ fileName }}</span> — {{ lineCount }} task(s) ready
            </p>
            <button type="button" class="admin-btn-ghost text-sm" @click="downloadTaskBulkTemplate">
              Download CSV template
            </button>
            <p class="admin-muted text-xs">
              CSV: columns <code class="font-mono">title</code> and optional
              <code class="font-mono">description</code>. Text: one task per line; use
              <code class="font-mono">|</code> before a description.
            </p>
          </div>

          <div v-else class="space-y-3">
            <textarea v-model="text" class="admin-input min-h-48 font-mono text-sm" />
            <div class="flex flex-wrap items-center gap-2">
              <button type="button" class="admin-btn-ghost text-sm" @click="useExample">
                Load example
              </button>
              <span class="admin-muted text-sm">{{ lineCount }} task(s)</span>
            </div>
          </div>

          <p v-if="fileError" class="admin-alert admin-alert--error">{{ fileError }}</p>

          <div class="flex gap-2 border-t border-slate-200 pt-4">
            <button type="button" class="admin-btn-secondary flex-1" @click="emit('close')">
              Cancel
            </button>
            <button type="button" class="admin-btn-primary flex-1" @click="submit">
              Import {{ lineCount }} task{{ lineCount === 1 ? '' : 's' }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>
