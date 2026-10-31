import type { Citation } from "@/lib/api/types"
import { citationPage } from "@/lib/api/source-url"

export async function copyText(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text)
    return true
  } catch {
    const focused = document.activeElement instanceof HTMLElement ? document.activeElement : null
    const selection = document.getSelection()
    const ranges = selection ? Array.from({ length: selection.rangeCount }, (_, i) => selection.getRangeAt(i).cloneRange()) : []
    const inputSelection = focused instanceof HTMLInputElement || focused instanceof HTMLTextAreaElement
      ? { start: focused.selectionStart, end: focused.selectionEnd, direction: focused.selectionDirection }
      : null
    const area = document.createElement("textarea")
    try {
      area.value = text
      area.setAttribute("readonly", "")
      area.style.position = "fixed"
      area.style.left = "-9999px"
      document.body.appendChild(area)
      area.select()
      return document.execCommand("copy")
    } catch {
      return false
    } finally {
      area.remove()
      focused?.focus()
      if (inputSelection && (focused instanceof HTMLInputElement || focused instanceof HTMLTextAreaElement) && inputSelection.start !== null && inputSelection.end !== null) {
        focused.setSelectionRange(inputSelection.start, inputSelection.end, inputSelection.direction ?? undefined)
      }
      if (selection) {
        selection.removeAllRanges()
        for (const range of ranges) selection.addRange(range)
      }
    }
  }
}

export function formatAnswerMarkdown(
  answer: string,
  citations: readonly Citation[]
): string {
  const lines = [answer.trim(), ""]
  if (citations.length > 0) {
    lines.push("## Citas")
    for (const citation of citations) {
      const page = citationPage(citation)
      const pagePart = page === undefined ? "" : `, p. ${page}`
      const section = citation.section ? ` — ${citation.section}` : ""
      lines.push(
        `- **${citation.doc}${section}${pagePart}**: ${citation.quote.trim()}`
      )
    }
    lines.push("")
  }
  return lines.join("\n")
}
