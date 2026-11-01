import type { RefusalData } from "./types"

export type RefusalCopy = { title: string; body: string }

/** The service's generic refusal sentence: it adds nothing the title does not say. */
const GENERIC_ANSWER = /^no dispongo de esa informaci[oó]n en los documentos\.?$/i

const NOT_FOUND = "Sin coincidencias en las facturas"
const MISSING = "Falta un dato en las facturas"
const NOT_UNDERSTOOD = "No he podido buscar eso en las facturas"

type Rule = { match: (reason: string) => boolean; title: string; hint: string }

/**
 * Internal reason codes become plain language here, and only here. The code itself stays
 * in the trace of the System page. First matching rule wins; the last one matches anything.
 */
const RULES: Rule[] = [
  { match: (r) => r === "empty_index", title: "Aún no hay fuentes", hint: "Sube un documento en Fuentes y vuelve a preguntar." },
  { match: (r) => r === "pregunta_vacia" || r === "pregunta_demasiado_larga", title: "Revisa la pregunta", hint: "Escribe una pregunta más corta." },
  {
    match: (r) => /^invoice:(factura_no_encontrada|parte_no_encontrada|sin_resultados|parte_rol_distinto)$/.test(r),
    title: NOT_FOUND,
    hint: "Comprueba el número o el nombre.",
  },
  {
    match: (r) => /^invoice:(campo_ausente|suma_datos_incompletos|campo_no_numerico)/.test(r),
    title: MISSING,
    hint: "Pregunta por otro dato de esa factura.",
  },
  {
    match: (r) => r.startsWith("invoice:"),
    title: NOT_UNDERSTOOD,
    hint: "Prueba con el número de factura o el nombre del emisor o del cliente.",
  },
  {
    match: () => true,
    title: "No lo encuentro en tus fuentes",
    hint: "Prueba con otras palabras o añade el documento que la contiene.",
  },
]

export function refusalCopy(refusal: RefusalData): RefusalCopy {
  const rule = RULES.find((candidate) => candidate.match(refusal.reason)) ?? RULES[RULES.length - 1]!
  const answer = refusal.answer.trim()
  const specific = answer.length > 0 && !GENERIC_ANSWER.test(answer)
  return { title: rule.title, body: specific ? answer : rule.hint }
}
