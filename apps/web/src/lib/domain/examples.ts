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
    id: sourceId("src-acme-demo-ds"),
    title: "ACME-DEMO-DS — Ficha técnica GR-50",
    excerpt:
      "Carga útil máxima: 12 kg (ISO 9409-1). Momento máximo en brida: 45 N·m. Interfaz ISO 9409-1-50-4-M6.",
    pageCount: 4,
  },
  {
    id: sourceId("src-cell-install"),
    title: "Manual de instalación — célula ACME-C12",
    excerpt:
      "La zona de seguridad debe mantener un perímetro libre de 800 mm alrededor del robot colaborativo durante el modo teach.",
    pageCount: 36,
  },
] as const satisfies readonly SourceDocument[]

export const exampleAnswer = {
  question: "¿Cuál es la carga útil máxima del GR-50?",
  body: "La carga útil máxima del end-effector GR-50 es de 12 kg según la ficha técnica ACME-DEMO-DS, sección 2.1.",
  citations: [
    {
      id: citationId("cit-1"),
      label: "ACME-DEMO-DS §2.1",
      sourceId: sourceId("src-acme-demo-ds"),
      page: 1,
    },
    {
      id: citationId("cit-2"),
      label: "ACME-DEMO-DS — brida",
      sourceId: sourceId("src-acme-demo-ds"),
      page: 1,
    },
  ],
} as const satisfies Answer

export const exampleRefusal = {
  reason: "No hay pasajes indexados que respondan a la consulta.",
  guidance:
    "No hay evidencia en los documentos indexados; no se inventa una respuesta. Reformula con el modelo, la sección o el parámetro concreto.",
} as const satisfies Refusal

export const exampleInvoice = {
  id: invoiceId("inv-2024-118"),
  vendor: "Robótica Norte S.L.",
  issuedOn: "2024-11-12",
  currency: "EUR",
  status: "flagged",
  total: 1452.0,
  lines: [
    {
      description: "Brida adaptadora ISO 9409-1",
      quantity: 2,
      unitPrice: 120.0,
      taxRate: 0.21,
    },
    {
      description: "Cableado GR-50 (kit)",
      quantity: 1,
      unitPrice: 980.0,
      taxRate: 0.21,
    },
  ],
  notes: "Revisar referencia de pedido en la página 1 del PDF.",
} as const satisfies InvoiceReview

export const exampleUploads = [
  {
    name: "ACME-DEMO-DS.pdf",
    sizeBytes: 248_832,
    mimeType: "application/pdf",
  },
  {
    name: "factura-brida.pdf",
    sizeBytes: 12_480,
    mimeType: "application/pdf",
  },
] as const satisfies readonly UploadFile[]
