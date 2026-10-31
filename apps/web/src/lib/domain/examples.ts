import type {
  Answer,
  CitationId,
  InvoiceId,
  InvoiceReview,
  Refusal,
  SourceDocument,
  SourceId,
  UploadFile,
} from "@/lib/domain/types"

const sourceId = (value: string) => value as SourceId
const citationId = (value: string) => value as CitationId
const invoiceId = (value: string) => value as InvoiceId

export const exampleSources = [
  {
    id: sourceId("src-iva-2024"),
    title: "Manual IVA 2024 — Cap. 3",
    excerpt:
      "Las facturas rectificativas deben identificar la factura original y el motivo de la rectificación. El tipo impositivo aplicable es el vigente en la fecha de la operación.",
    pageCount: 42,
  },
  {
    id: sourceId("src-modelo-303"),
    title: "Instrucciones Modelo 303",
    excerpt:
      "En la casilla 28 se consignará el IVA deducible en operaciones interiores. No incluir cuotas soportadas en adquisiciones de bienes de inversión.",
    pageCount: 18,
  },
] as const satisfies readonly SourceDocument[]

export const exampleAnswer = {
  question: "¿Puedo deducir el IVA de esta factura de material de oficina?",
  body: "Sí, el IVA soportado en material de oficina es deducible si la factura cumple los requisitos formales y el gasto está afecto a la actividad. Conserva el justificante y consúltalo en la casilla correspondiente del modelo 303.",
  citations: [
    {
      id: citationId("cit-1"),
      label: "Manual IVA §3.2",
      sourceId: sourceId("src-iva-2024"),
      page: 14,
    },
    {
      id: citationId("cit-2"),
      label: "Modelo 303 — casilla 28",
      sourceId: sourceId("src-modelo-303"),
      page: 7,
    },
  ],
} as const satisfies Answer

export const exampleRefusal = {
  reason: "La consulta pide una estrategia de elusión fiscal.",
  guidance:
    "Reformula la pregunta sobre obligaciones, plazos o requisitos formales. Puedo ayudarte a interpretar la normativa publicada, no a eludirla.",
} as const satisfies Refusal

export const exampleInvoice = {
  id: invoiceId("inv-2024-118"),
  vendor: "Papelería Norte S.L.",
  issuedOn: "2024-11-12",
  currency: "EUR",
  status: "flagged",
  total: 145.2,
  lines: [
    {
      description: "Resmas A4 80g (pack 5)",
      quantity: 4,
      unitPrice: 12.5,
      taxRate: 0.21,
    },
    {
      description: "Tóner compatible HP 85A",
      quantity: 2,
      unitPrice: 38.0,
      taxRate: 0.21,
    },
  ],
  notes: "Falta NIF del destinatario en la copia OCR.",
} as const satisfies InvoiceReview

export const exampleUploads = [
  {
    name: "factura-papeleria.pdf",
    sizeBytes: 248_832,
    mimeType: "application/pdf",
  },
  {
    name: "extracto-noviembre.csv",
    sizeBytes: 12_480,
    mimeType: "text/csv",
  },
] as const satisfies readonly UploadFile[]
