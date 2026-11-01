import type { Block, Cell, Citation, FollowUp, KeyDataBlock, TableBlock } from "./types"

function record(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value)
}

function kind(value: unknown): value is Cell["kind"] {
  return value === "text" || value === "date" || value === "amount" || value === "percent" || value === "id"
}

function cell(value: unknown, citations: readonly Citation[], docId: string, field: string): Cell | null {
  if (!record(value) || !kind(value.kind)) return null
  if (value.text === null && value.cite == null) return { text: null, kind: value.kind, cite: null }
  if (typeof value.text !== "string" || !value.text || typeof value.cite !== "number" || !Number.isInteger(value.cite)) return null
  const citation = citations[value.cite]
  if (!citation || citation.doc_id !== docId || citation.section !== field || citation.quote !== value.text) return null
  return { text: value.text, kind: value.kind, cite: value.cite }
}

function keyData(value: Record<string, unknown>, citations: readonly Citation[]): KeyDataBlock | null {
  if (typeof value.title !== "string" || typeof value.doc_id !== "string" || !Array.isArray(value.items) || !value.items.length) return null
  if (value.note != null && typeof value.note !== "string") return null
  const items: KeyDataBlock["items"] = []
  for (const item of value.items) {
    if (!record(item) || typeof item.field !== "string" || typeof item.label !== "string") return null
    const parsed = cell(item, citations, value.doc_id, item.field)
    if (!parsed || items.some((other) => other.field === item.field)) return null
    items.push({ ...parsed, field: item.field, label: item.label })
  }
  return { type: "key_data", title: value.title, doc_id: value.doc_id, items, note: value.note ?? null }
}

function table(value: Record<string, unknown>, citations: readonly Citation[]): TableBlock | null {
  if (!Array.isArray(value.columns) || !value.columns.length || !Array.isArray(value.rows) || !value.rows.length) return null
  if (value.title != null && typeof value.title !== "string") return null
  if (value.note != null && typeof value.note !== "string") return null
  const columns: TableBlock["columns"] = []
  for (const column of value.columns) {
    if (!record(column) || typeof column.key !== "string" || typeof column.label !== "string" || !kind(column.kind)) return null
    if (columns.some((other) => other.key === column.key)) return null
    columns.push({ key: column.key, label: column.label, kind: column.kind })
  }
  if (columns[0]?.key !== "numero") return null
  const rows: TableBlock["rows"] = []
  for (const row of value.rows) {
    if (!record(row) || typeof row.doc_id !== "string" || typeof row.question !== "string" || !row.question.trim()) return null
    if (!Array.isArray(row.cells) || row.cells.length !== columns.length || rows.some((other) => other.doc_id === row.doc_id)) return null
    const cells: Cell[] = []
    for (const [index, item] of row.cells.entries()) {
      const column = columns[index]
      if (!column) return null
      const parsed = cell(item, citations, row.doc_id, column.key)
      if (!parsed || parsed.kind !== column.kind) return null
      cells.push(parsed)
    }
    rows.push({ doc_id: row.doc_id, question: row.question, cells })
  }
  let summary: TableBlock["summary"] = null
  if (value.summary != null) {
    const item = value.summary
    if (!record(item) || item.operation !== "sum" || item.kind !== "amount" || typeof item.label !== "string" || typeof item.text !== "string" || !Array.isArray(item.refs)) return null
    const refs: number[] = []
    for (const ref of item.refs) {
      if (typeof ref !== "number" || !Number.isInteger(ref) || !citations[ref]) return null
      refs.push(ref)
    }
    if (columns.length < 2 || columns.at(-1)?.kind !== "amount" || refs.length !== rows.length) return null
    if (rows.some((row, index) => row.cells.at(-1)?.cite !== refs[index])) return null
    summary = { label: item.label, text: item.text, kind: "amount", operation: "sum", refs }
  }
  return { type: "table", title: value.title ?? null, columns, rows, summary, note: value.note ?? null }
}

/** A partial representation could hide answer text, so any invalid block rejects the whole set. */
export function usableBlocks(value: unknown, citations: readonly Citation[]): Block[] {
  if (!Array.isArray(value)) return []
  const out: Block[] = []
  for (const item of value) {
    if (!record(item)) return []
    const parsed = item.type === "key_data" ? keyData(item, citations) : item.type === "table" ? table(item, citations) : null
    if (!parsed) return []
    out.push(parsed)
  }
  return out
}

export function usableFollowUps(value: unknown): FollowUp[] {
  if (!Array.isArray(value)) return []
  return value.flatMap((item) => record(item) && typeof item.label === "string" && typeof item.question === "string" && item.question.trim() ? [{ label: item.label, question: item.question }] : [])
}

export const EMPTY_CELL = "—"
export const cellText = (cell: Cell): string => cell.text ?? EMPTY_CELL
const tsvCell = (text: string): string => /[\t\r\n"]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text

export function tableTsv(block: TableBlock): string {
  const header = block.columns.map((column) => tsvCell(column.label)).join("\t")
  const rows = block.rows.map((row) => row.cells.map((cell) => tsvCell(cellText(cell))).join("\t"))
  const footer = block.summary ? [[block.summary.label, ...Array<string>(Math.max(0, block.columns.length - 2)).fill(""), block.summary.text].map(tsvCell).join("\t")] : []
  return [header, ...rows, ...footer, ...(block.note ? [tsvCell(block.note)] : [])].join("\n")
}

export function blockText(block: Block): string {
  if (block.type === "key_data") {
    return [block.title, ...block.items.map((item) => `${item.label}: ${cellText(item)}`), block.note].filter(Boolean).join("\n")
  }
  return [block.title, tableTsv(block)].filter(Boolean).join("\n")
}
