/**
 * Wraps amounts ("1.706,60 €") and dates ("14/02/2026", "2026-02-14") of a Markdown answer in a span
 * so they read as tabular figures. The text is never changed: only its wrapper is. Code, links and
 * existing figures are left alone.
 */
const FIGURE = /\d{1,3}(?:\.\d{3})*,\d{2}\s?€|\d+,\d{2}\s?€|\b\d{2}\/\d{2}\/\d{4}\b|\b\d{4}-\d{2}-\d{2}\b/g
const SKIP = new Set(["code", "pre", "a", "button", "kbd", "script", "style"])

type HastNode = {
  type: string
  tagName?: string
  value?: string
  properties?: Record<string, unknown>
  children?: HastNode[]
}

function figureNodes(text: string): HastNode[] | null {
  const out: HastNode[] = []
  let last = 0
  for (const match of text.matchAll(FIGURE)) {
    const start = match.index ?? 0
    if (start > last) out.push({ type: "text", value: text.slice(last, start) })
    const kind = match[0].includes("€") ? "amount" : "date"
    out.push({
      type: "element",
      tagName: "span",
      properties: { className: ["figure", `figure-${kind}`], "data-figure": kind },
      children: [{ type: "text", value: match[0] }],
    })
    last = start + match[0].length
  }
  if (out.length === 0) return null
  if (last < text.length) out.push({ type: "text", value: text.slice(last) })
  return out
}

function walk(node: HastNode): void {
  if (!node.children || (node.tagName && SKIP.has(node.tagName))) return
  const next: HastNode[] = []
  for (const child of node.children) {
    const pieces = child.type === "text" && child.value ? figureNodes(child.value) : null
    if (pieces) next.push(...pieces)
    else {
      walk(child)
      next.push(child)
    }
  }
  node.children = next
}

export function rehypeFigures() {
  return (tree: HastNode) => walk(tree)
}
