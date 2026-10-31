export function sourcePageUrl(docId: string, page: number): string {
  return `/api/sources/${encodeURIComponent(docId)}/pages/${page}`
}

export function citationPage(
  citation: { pages: number[] },
  index = 0
): number | undefined {
  const pages = citation.pages
  if (pages.length === 0) return undefined
  return pages[Math.min(Math.max(index, 0), pages.length - 1)]
}

export function invoiceImageUrl(invoiceId: string): string {
  return `/api/invoices/${encodeURIComponent(invoiceId)}/image`
}
