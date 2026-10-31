import type { AskResponse, ErrorBody } from "../src/lib/api/types"

export const askAnswerWithCitation = {
  ok: true,
  answer:
    "El IVA soportado en material de oficina es deducible si la factura cumple los requisitos formales.",
  citations: [
    {
      chunk_id: "chunk-iva-1",
      quote: "requisitos formales de la factura",
      doc: "Manual IVA 2024",
      section: "§3.2",
      pages: [14],
      fragment:
        "Las facturas deben cumplir los requisitos formales de la factura y el gasto ha de estar afecto a la actividad.",
    },
  ],
  reason: "",
} as const satisfies AskResponse

export const askRefusal = {
  ok: false,
  answer: "",
  citations: [],
  reason: "La consulta pide una estrategia de elusión fiscal.",
} as const satisfies AskResponse

export const askError = {
  code: "adapter_error",
  message: "El modelo no está disponible.",
} as const satisfies ErrorBody

/** 64×40 PNG gris sólido (determinista para capturas). */
export const PAGE_PNG_BASE64 =
  "iVBORw0KGgoAAAANSUhEUgAAAeAAAAEYCAIAAAALd7K2AAAG20lEQVR42u3U0QnAMAxDQc/Z2btBluhHVwiRCKcJDhvePGZmVrlxAjMzgTYzM4E2MxNoMzMTaDMzgTYzM4E2MzOBNjMTaDMzE2gzM4E2MzOBNjMzgTYzE2gzMxNoMzOBNjMzgTYzE2gzMxNoMzMTaDMzgTYzM4E2MxNoMzMTaDMzE2gzM4E2MzOBNjMTaDMzE2gzM4E2MzOBNjMzgTYzE2gzMxNoMzOBNjOzaKDfTVubxsPDw8PzT6B5eHh4BNrDeHh4eASah4eHR6A9jIeHh0egeXh4eATagXh4eHgE2sN4eHh4BJqHh4dHoD2Mh4eHR6B5eHh4BNrDeHh4eM4H2qF5eHh4Oj0CzcPDwyPQHsbDw8Mj0Dw8PDwC7WE8PDw8As3Dw8Mj0A7Ew8PDI9AexsPDwyPQPDw8PALtYTw8PDwCzcPDwyPQHsbDw8Mj0Dw8PDw8As3Dw8Mj0B7Gw8PDI9A8PDw8Au1hPDw8PALNw8PDI9AOxMPDwyPQHsbDw8Mj0Dw8PDwC7WE8PDw8As3Dw8Mj0B7Gw8PDkwq0Q/Pw8PB0egSah4eHR6A9jIeHh0egeXh4eATaw3h4eHgEmoeHh0egHYiHh4dHoD2Mh4eHR6B5eHh4BNrDeHh4eASah4eHR6A9jIeHh0egeXh4eHgEmoeHh0egPYyHh4dHoHl4eHgE2sN4eHh4BJqHh4dHoB2Ih4eHR6A9jIeHh0egeXh4eATaw3h4eHgEmoeHh0egPYyHh4cnFWiH5uHh4en0CDQPDw+PQHsYDw8Pj0Dz8PDwCLSH8fDw8Ag0Dw8Pj0A7EA8PD49AexgPDw+PQPPw8PAItIfx8PDwCDQPDw+PQHsYDw8Pj0Dz8PDw8Ag0Dw8Pj0B7GA8PD49A8/Dw8Ai0h/Hw8PAINA8PD49AOxAPDw+PQHsYDw8Pj0Dz8PDwCLSH8fDw8Ag0Dw8Pj0B7GA8PD08q0A7Nw8PD0+kRaB4eHh6B9jAeHh4egebh4eERaA/j4eHhEWgeHh4egXYgHh4eHoH2MB4eHh6B5uHh4RFoD+Ph4eERaB4eHh6B9jAeHh4egebh4eHhEWgeHh4egfYwHh4eHoHm4eHhEWgP4+Hh4RFoHh4eHoF2IB4eHh6B9jAeHh4egebh4eERaA/j4eHhEWgeHh4egfYwHh4enlSgHZqHh4en0yPQPDw8PALtYTw8PDwCzcPDwyPQHsbDw8Mj0Dw8PDwC7UA8PDw8Au1hPDw8PALNw8PDI9AexsPDwyPQPDw8PALtYTw8PDwCzcPDw8Mj0Dw8PDwC7WE8PDw8As3Dw8Mj0B7Gw8PDI9A8PDw8Au1APDw8PALtYTw8PDwCzcPDwyPQHsbDw8Mj0Dw8PDwC7WE8PDw8qUA7NA8PD0+nR6B5eHh4BNrDeHh4eASah4eHR6A9jIeHh0egeXh4eATagXh4eHgE2sN4eHh4BJqHh4dHoD2Mh4eHR6B5eHh4BNrDeHh4eASah4eHh0egeXh4eATaw3h4eHgEmoeHh0egPYyHh4dHoHl4eHgE2oF4eHh4BNrDeHh4eASah4eHR6A9jIeHh0egeXh4eATaw3h4eHhSgXZoHh4enk6PQPPw8PAItIfx8PDwCDQPDw+PQHsYDw8Pj0Dz8PDwCLQD8fDw8Ai0h/Hw8PAINA8PD49AexgPDw+PQPPw8PAItIfx8PDwCDQPDw8Pj0Dz8PDwCLSH8fDw8Ag0Dw8Pj0B7GA8PD49A8/Dw8Ai0A/Hw8PAItIfx8PDwCDQPDw+PQHsYDw8Pj0Dz8PDwCLSH8fDw8KQC7dA8PDw8nR6B5uHh4RFoD+Ph4eERaB4eHh6B9jAeHh4egebh4eERaAfi4eHhEWgP4+Hh4RFoHh4eHoH2MB4eHh6B5uHh4RFoD+Ph4eERaB4eHh4egebh4eERaA/j4eHhEWgeHh4egfYwHh4eHoHm4eHhEWgH4uHh4RFoD+Ph4eERaB4eHh6B9jAeHh4egebh4eERaA/j4eHhSQXaoXl4eHg6PQLNw8PDI9AexsPDwyPQPDw8PALtYTw8PDwCzcPDwyPQDsTDw8Mj0B7Gw8PDI9A8PDw8Au1hPDw8PALNw8PDI9AexsPDwyPQPDw8PDwCzcPDwyPQHsbDw8Mj0Dw8PDwC7WE8PDw8As3Dw8Mj0A7Ew8PDI9AexsPDwyPQPDw8PALtYTw8PDwCzcPDwyPQHsbDw8OTCrRD8/Dw8HR6BJqHh4dHoD2Mh4eHR6B5eHh4BNrDeHh4eASah4eHR6AdiIeHh0egPYyHh4dHoHl4eHgE2sN4eHh4BJqHh4dHoD2Mh4eHR6B5eHh4eASah4eHR6A9jIeHh0egeXh4eK7xfCBQMGZtjxCkAAAAAElFTkSuQmCC"
