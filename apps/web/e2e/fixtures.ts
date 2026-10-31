import fs from "node:fs"
import path from "node:path"

import type { AskResponse, ErrorBody } from "../src/lib/api/types"

export const DEMO_QUESTION = "¿Cuál es la carga útil máxima del GR-50?"

export const askAnswerWithCitation = {
  ok: true,
  answer:
    "La carga útil máxima del pinza GR-50 es de 12 kg (ISO 9409-1), según la ficha técnica ACME-DEMO-DS.",
  citations: [
    {
      chunk_id: "chunk-acme-ds-2-1",
      quote: "Carga útil máxima: 12 kg",
      doc: "ACME-DEMO-DS",
      doc_id: "pdf-acme-demo-ds",
      section: "2.1",
      pages: [1],
      fragment:
        "2.1 Capacidad de carga útil. Carga útil máxima: 12 kg (ISO 9409-1). Momento máximo en brida: 45 N·m.",
    },
    {
      chunk_id: "chunk-acme-ds-flange",
      quote: "ISO 9409-1-50-4-M6",
      doc: "ACME-DEMO-DS",
      doc_id: "pdf-acme-demo-ds",
      section: "2.1",
      pages: [1],
      fragment:
        "Interfaz brida: ISO 9409-1-50-4-M6. Grado de protección IP54. Temperatura de trabajo 0 … 45 °C.",
    },
  ],
  reason: "",
} as const satisfies AskResponse

export const askRefusal = {
  ok: false,
  answer: "No dispongo de esa información en los documentos",
  citations: [],
  reason: "llm_unanswerable",
} as const satisfies AskResponse

export const askError = {
  code: "adapter_error",
  message: "El modelo no está disponible.",
} as const satisfies ErrorBody

/** Página sintética de ficha técnica (generada, no checkerboard). */
export const PAGE_PNG = fs.readFileSync(
  path.join(process.cwd(), "e2e", "fixtures", "page-acme-demo-ds.png")
)
