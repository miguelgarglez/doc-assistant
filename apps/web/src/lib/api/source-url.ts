export function sourcePageUrl(docId: string, page: number): string {
  return `/api/sources/${encodeURIComponent(docId)}/pages/${page}`
}

export function citationPage(citation: { pages: number[] }): number | undefined {
  return citation.pages[0]
}
