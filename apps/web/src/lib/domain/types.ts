export type CitationId = string & { readonly __brand: "CitationId" }
export type SourceId = string & { readonly __brand: "SourceId" }
export type InvoiceId = string & { readonly __brand: "InvoiceId" }

export type Citation = {
  id: CitationId
  label: string
  sourceId: SourceId
  page?: number
}

export type SourceDocument = {
  id: SourceId
  title: string
  excerpt: string
  pageCount: number
}

export type Answer = {
  question: string
  body: string
  citations: Citation[]
}

export type Refusal = {
  reason: string
  guidance: string
}

export type InvoiceLine = {
  description: string
  quantity: number
  unitPrice: number
  taxRate: number
}

export type InvoiceReview = {
  id: InvoiceId
  vendor: string
  issuedOn: string
  currency: string
  status: "pending" | "approved" | "flagged"
  total: number
  lines: InvoiceLine[]
  notes?: string
}

export type UploadFile = {
  name: string
  sizeBytes: number
  mimeType: string
}
