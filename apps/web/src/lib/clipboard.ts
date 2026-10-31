import type { Citation } from "@/lib/api/types"
import { citationPage } from "@/lib/api/source-url"

export async function copyText(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text)
    return true
  } catch {
    try {
      const area = document.createElement("textarea")
      area.value = text
      area.setAttribute("readonly", "")
      area.style.position = "fixed"
      area.style.left = "-9999px"
      document.body.appendChild(area)
      area.select()
      const ok = document.execCommand("copy")
      document.body.removeChild(area)
      return ok
    } catch {
      return false
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
