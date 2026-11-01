"use client"

import { useCallback, useEffect, useRef, useState } from "react"
import { toast } from "sonner"
import { Button, buttonVariants } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { Field, FieldDescription, FieldGroup, FieldLabel } from "@/components/ui/field"
import { Textarea } from "@/components/ui/textarea"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { isEditableTarget } from "@/lib/shortcuts"

type Status = "nuevo" | "revisado" | "descartado"
type Cause = "no_recupero" | "respuesta_incorrecta" | "rechazo_indebido" | "formato" | "otro"
type Item = { feedback_id: string; request_id: string; conversation_id: string; created_at: string; kind: string; comment: string | null; status: Status; expected_answer: string | null; trace: Record<string, unknown>; review_cause?: Cause | null; export_preview?: Record<string, unknown> | null }
type Citation = { doc?: string; section?: string; quote?: string; fragment?: string; pages?: number[] }
type Original = { question?: string; result?: { answer?: string; citations?: Citation[] }; steps?: { label?: string; status?: string; elapsed_s?: number }[] }
const statusLabels: Record<Status, string> = { nuevo: "Pendientes", revisado: "Revisados", descartado: "Descartados" }
const causes: { value: Cause; label: string }[] = [{ value: "no_recupero", label: "No recuperó información" }, { value: "respuesta_incorrecta", label: "Respuesta incorrecta" }, { value: "rechazo_indebido", label: "Rechazo indebido" }, { value: "formato", label: "Formato" }, { value: "otro", label: "Otro" }]
const sensitive = /(\b[A-Z]{2}\d{2}(?:[ ]?\d){10,30}\b|\b\d{8}[A-Z]\b|\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b|(?:\+\d{1,3}[ .-]?)?(?:\d[ .-]?){9,12}|\b\d+(?:[.,]\d+)?\s?(?:€|EUR)|\b[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)+\b)/g
function Highlight({ text }: { text: string }) {
  return <>{text.split(sensitive).map((part, index) => index % 2 ? <mark key={index} className="rounded-sm bg-amber-200 text-black">{part}</mark> : part)}</>
}

export default function ReviewPage() {
  const [filter, setFilter] = useState<Status>("nuevo")
  const [items, setItems] = useState<Item[]>([])
  const [counts, setCounts] = useState<Record<string, number>>({})
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [detail, setDetail] = useState<Item | null>(null)
  const [original, setOriginal] = useState<Original | null>(null)
  const [originalMissing, setOriginalMissing] = useState(false)
  const [loading, setLoading] = useState(true)
  const [detailLoading, setDetailLoading] = useState(false)
  const [error, setError] = useState("")
  const [saving, setSaving] = useState(false)
  const [answer, setAnswer] = useState("")
  const [comment, setComment] = useState("")
  const [context, setContext] = useState("")
  const [cause, setCause] = useState<Cause>("respuesta_incorrecta")
  const [confirmed, setConfirmed] = useState(false)
  const [safe, setSafe] = useState(false)
  const [offset, setOffset] = useState(0)
  const [hasMore, setHasMore] = useState(false)
  const loadVersion = useRef(0)

  const load = useCallback(async (current: Status, nextOffset = 0, append = false) => {
    const version = ++loadVersion.current
    setLoading(true); setError("")
    try {
      const [queue, totals] = await Promise.all([fetch(`/api/history/feedback?status=${current}&limit=50&offset=${nextOffset}`), fetch("/api/history/feedback/counts")])
      if (!queue.ok || !totals.ok) throw new Error()
      const rows: Item[] = await queue.json()
      const newCounts: Record<string, number> = await totals.json()
      if (version !== loadVersion.current) return
      setCounts(newCounts); setItems((previous) => append ? [...previous, ...rows] : rows)
      setOffset(nextOffset + rows.length); setHasMore(rows.length === 50)
      if (!append) setSelectedId((id) => rows.some((row) => row.feedback_id === id) ? id : rows[0]?.feedback_id ?? null)
    } catch { if (version === loadVersion.current) setError("No se pudo cargar la cola. Inténtalo de nuevo.") }
    finally { if (version === loadVersion.current) setLoading(false) }
  }, [])
  useEffect(() => { void Promise.resolve().then(() => { const id = new URLSearchParams(window.location.search).get("id"); if (id && filter === "nuevo") setSelectedId(id); void load(filter) }) }, [filter, load])
  useEffect(() => {
    if (!selectedId) return
    const controller = new AbortController()
    void Promise.resolve().then(() => { setDetailLoading(true); setDetail(null); setOriginal(null); setOriginalMissing(false) })
    void (async () => {
      try {
        const response = await fetch(`/api/history/feedback/${encodeURIComponent(selectedId)}`, { signal: controller.signal })
        if (!response.ok) throw new Error()
        const item: Item = await response.json()
        const source = await fetch(`/api/history/feedback/${encodeURIComponent(selectedId)}/original`, { signal: controller.signal })
        if (!source.ok && source.status !== 404) throw new Error()
        const request: Original | null = source.ok ? await source.json() : null
        if (controller.signal.aborted) return
        setDetail(item); setOriginal(request); setOriginalMissing(!source.ok)
        setAnswer(item.expected_answer ?? "")
        setComment(typeof item.export_preview?.comment === "string" ? item.export_preview.comment : item.comment ?? "")
        setContext(typeof item.export_preview?.redacted_context === "string" ? item.export_preview.redacted_context : "")
        setCause(item.review_cause ?? "respuesta_incorrecta"); setConfirmed(false); setSafe(false)
      } catch { if (!controller.signal.aborted) setError("No se pudo cargar el aviso.") }
      finally { if (!controller.signal.aborted) setDetailLoading(false) }
    })()
    return () => controller.abort()
  }, [selectedId])

  const move = useCallback((direction: number) => {
    const index = items.findIndex((item) => item.feedback_id === selectedId)
    const next = items[index + direction]
    if (next) setSelectedId(next.feedback_id)
  }, [items, selectedId])
  const decide = useCallback(async (status: Status) => {
    if (!detail || saving) return
    if (status === "revisado" && (!answer.trim() || !confirmed || !safe)) { toast.error("Completa la respuesta y las confirmaciones de revisión."); return }
    const old = detail
    setSaving(true); setDetail({ ...detail, status })
    try {
      const response = await fetch(`/api/history/feedback/${encodeURIComponent(detail.feedback_id)}/decision`, {
        method: "PUT", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status, expected_answer: answer, cause, redacted_comment: comment || null, redacted_context: context || null, confirmed_error: confirmed, confirmed_no_sensitive_data: safe }),
      })
      if (!response.ok) throw new Error()
      toast.success(status === "revisado" ? "Aviso revisado" : status === "descartado" ? "Aviso descartado" : "Aviso devuelto a pendientes")
      await load(filter)
    } catch { setDetail(old); toast.error("No se pudo guardar; se ha restaurado el estado anterior.") }
    finally { setSaving(false) }
  }, [detail, saving, answer, confirmed, safe, cause, comment, context, filter, load])
  useEffect(() => {
    function key(event: KeyboardEvent) {
      if (event.defaultPrevented || event.metaKey || event.ctrlKey || event.altKey || isEditableTarget(event.target) || document.querySelector('[role="dialog"]')) return
      if (event.key === "j") move(1)
      if (event.key === "k") move(-1)
      if (event.key === "a") void decide("revisado")
      if (event.key === "d") void decide("descartado")
    }
    window.addEventListener("keydown", key); return () => window.removeEventListener("keydown", key)
  }, [move, decide])
  const preview = detail ? { feedback_id: detail.feedback_id, request_id: detail.request_id, conversation_id: detail.conversation_id, created_at: detail.created_at, kind: detail.kind, status: "revisado", comment: comment || null, trace: { request_id: detail.request_id, conversation_id: detail.conversation_id }, expected_answer: answer, cause, redacted_context: context || null } : null
  const index = items.findIndex((item) => item.feedback_id === selectedId)
  return <div className="flex min-h-0 flex-1 flex-col">
    <header className="flex flex-wrap items-center justify-between gap-3 border-b px-6 py-4"><div><h1 className="font-heading text-xl font-semibold">Revisión de avisos</h1><p className="text-sm text-muted-foreground">Comprueba el fallo y prepara una copia segura para exportar.</p></div><a className={buttonVariants({ variant: "outline", size: "sm" })} href="/api/history/feedback/export" download="feedback-revisado.jsonl">Exportar revisados</a></header>
    <div className="grid min-h-0 flex-1 md:grid-cols-[20rem_minmax(0,1fr)]">
      <aside aria-label="Cola de avisos" className="flex min-h-0 flex-col gap-3 border-r p-4"><Tabs value={filter} onValueChange={(value) => { if (value === "nuevo" || value === "revisado" || value === "descartado") { setSelectedId(null); setDetail(null); setFilter(value) } }}><TabsList>{(Object.keys(statusLabels) as Status[]).map((value) => <TabsTrigger key={value} value={value} disabled={saving}>{statusLabels[value]} {counts[value] ?? 0}</TabsTrigger>)}</TabsList></Tabs>
        <p className="text-xs text-muted-foreground">j / k siguiente o anterior · a revisar · d descartar · ? ayuda</p>
        {loading ? <p role="status">Cargando avisos…</p> : null}{error ? <p role="alert">{error} <Button size="sm" variant="outline" onClick={() => void load(filter)}>Reintentar</Button></p> : null}
        {!loading && !items.length && !error ? <p className="text-sm text-muted-foreground">No hay avisos en esta categoría.</p> : null}
        <div className="min-h-0 flex-1 overflow-y-auto"><ul className="flex flex-col">{items.map((item) => <li key={item.feedback_id}><button type="button" aria-current={selectedId === item.feedback_id ? "true" : undefined} className="w-full border-b px-2 py-3 text-left text-sm hover:bg-muted aria-current:bg-muted" onClick={() => setSelectedId(item.feedback_id)}><span className="block truncate font-medium">{item.comment || "Sin comentario"}</span><span className="text-xs text-muted-foreground">{new Date(item.created_at).toLocaleString("es-ES")}</span></button></li>)}</ul>{hasMore ? <Button disabled={loading} variant="ghost" onClick={() => void load(filter, offset, true)}>Cargar más</Button> : null}</div>
      </aside>
      <section aria-label="Detalle de revisión" className="min-h-0 overflow-y-auto p-6">{detailLoading ? <p role="status">Cargando detalle…</p> : null}{!detailLoading && !detail ? <p className="text-muted-foreground">Selecciona un aviso para revisarlo.</p> : null}{detail ? <div className="mx-auto flex max-w-4xl flex-col gap-6">
        <div className="flex flex-wrap items-start justify-between gap-3"><div><h2 className="font-heading text-lg font-semibold">Detalle del aviso</h2><p className="break-all text-xs text-muted-foreground">Petición: {detail.request_id} · Conversación: {detail.conversation_id}</p></div><div className="flex gap-2"><Button size="sm" variant="outline" disabled={index <= 0} onClick={() => move(-1)}>Anterior</Button><Button size="sm" variant="outline" disabled={index < 0 || index >= items.length - 1} onClick={() => move(1)}>Siguiente</Button></div></div>
        <section className="flex flex-col gap-3"><h3 className="font-semibold">Conversación original</h3>{originalMissing ? <p>La conversación original ya no está disponible. El aviso conserva su captura.</p> : null}<div><p className="text-xs font-medium text-muted-foreground">Pregunta</p><p className="whitespace-pre-wrap"><Highlight text={original?.question ?? "No disponible"} /></p></div><div><p className="text-xs font-medium text-muted-foreground">Respuesta</p><p className="whitespace-pre-wrap"><Highlight text={original?.result?.answer ?? "No disponible"} /></p></div>{original?.result?.citations?.map((citation, i) => <div className="border-l-2 pl-3 text-sm" key={i}><p className="font-medium">{citation.doc ?? "Documento"} {citation.section ? `· ${citation.section}` : ""} {citation.pages?.length ? `· pág. ${citation.pages.join(", ")}` : ""}</p><p className="whitespace-pre-wrap"><Highlight text={citation.fragment || citation.quote || "Sin fragmento"} /></p></div>)}
          {original?.steps?.length ? <div><p className="text-sm font-medium">Traza</p><ul className="text-sm text-muted-foreground">{original.steps.map((step, i) => <li key={i}>{step.label ?? "Paso"} · {step.status ?? "—"} {step.elapsed_s == null ? "" : `· ${step.elapsed_s} s`}</li>)}</ul></div> : null}<details><summary className="cursor-pointer text-sm font-medium">Ver JSON original</summary><pre className="overflow-x-auto whitespace-pre-wrap break-words rounded-md bg-muted p-3 text-xs">{JSON.stringify(original ?? detail.trace, null, 2)}</pre></details>
        </section>
        <section className="flex flex-col gap-4 border-t pt-5"><div><h3 className="font-semibold">Preparar la revisión</h3><p className="text-sm text-muted-foreground">Se resaltan posibles datos sensibles, incluidos nombres, importes, IBAN, NIF, correos y teléfonos. La detección puede omitir datos: revisa todo antes de confirmar.</p></div>
          <FieldGroup><Field><FieldLabel htmlFor="cause">Causa del fallo</FieldLabel><select id="cause" className="h-9 rounded-md border border-input bg-background px-3 text-sm" value={cause} onChange={(e) => { setCause(e.target.value as Cause); setSafe(false) }}>{causes.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select></Field>
            <Field><FieldLabel htmlFor="answer">Respuesta esperada</FieldLabel><FieldDescription>Describe la respuesta correcta sin incluir datos personales ni importes identificables.</FieldDescription><Textarea id="answer" value={answer} maxLength={4000} onChange={(e) => { setAnswer(e.target.value); setSafe(false) }} /><p className="whitespace-pre-wrap text-sm"><Highlight text={answer} /></p></Field>
            <Field><FieldLabel htmlFor="comment">Comentario para exportar</FieldLabel><Textarea id="comment" value={comment} maxLength={4000} onChange={(e) => { setComment(e.target.value); setSafe(false) }} /><p className="text-sm"><Highlight text={comment} /></p></Field>
            <Field><FieldLabel htmlFor="context">Contexto redactado para exportar (opcional)</FieldLabel><FieldDescription>Escribe únicamente los fragmentos que quieras compartir tras quitar los datos sensibles. La conversación original no se exporta.</FieldDescription><Textarea id="context" value={context} maxLength={40000} onChange={(e) => { setContext(e.target.value); setSafe(false) }} /><p className="whitespace-pre-wrap text-sm"><Highlight text={context} /></p></Field>
            <Field orientation="horizontal"><Checkbox id="confirmed" checked={confirmed} onCheckedChange={setConfirmed} /><FieldLabel htmlFor="confirmed">He comprobado que hay un fallo real.</FieldLabel></Field>
            <Field orientation="horizontal"><Checkbox id="safe" checked={safe} onCheckedChange={setSafe} /><FieldLabel htmlFor="safe">He revisado toda la vista previa y quitado los datos sensibles.</FieldLabel></Field>
          </FieldGroup>
          <details><summary className="cursor-pointer text-sm font-medium">Vista previa del registro JSONL</summary><pre className="overflow-x-auto whitespace-pre-wrap break-words rounded-md bg-muted p-3 text-xs">{JSON.stringify(preview, null, 2)}</pre></details>
          <div className="flex flex-wrap gap-2"><Button disabled={saving || !answer.trim() || !confirmed || !safe} onClick={() => void decide("revisado")}>Marcar revisado</Button><Button disabled={saving} variant="outline" onClick={() => void decide("descartado")}>Descartar</Button><Button disabled={saving} variant="ghost" onClick={() => void decide("nuevo")}>Volver a pendiente</Button>{saving ? <span role="status">Guardando…</span> : null}</div>
        </section>
      </div> : null}</section>
    </div>
  </div>
}
