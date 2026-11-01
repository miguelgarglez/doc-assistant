"use client"

import { useCallback, useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { toast } from "sonner"

import { useConversation } from "@/components/providers/chat-provider"
import { Button, buttonVariants } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"

type HistoryStatus = { active: boolean; retention_days: number; pending: number; failures: { request_id: string; error: string }[] }
type Feedback = { feedback_id: string; conversation_id: string; request_id: string; created_at: string; comment: string | null; trace: Record<string, unknown> }

export function HistoryStatusPanel() {
  const router = useRouter()
  const { openConversation, busy } = useConversation()
  const [status, setStatus] = useState<HistoryStatus | null>(null)
  const [feedback, setFeedback] = useState<Feedback[]>([])
  const [hasMore, setHasMore] = useState(false)
  const [selected, setSelected] = useState<Feedback | null>(null)
  const [answer, setAnswer] = useState("")
  const [confirmedError, setConfirmedError] = useState(false)
  const [confirmedSafe, setConfirmedSafe] = useState(false)
  const [error, setError] = useState("")
  const [saving, setSaving] = useState(false)

  const refresh = useCallback(async () => {
    try {
      const response = await fetch("/api/history/status")
      if (!response.ok) throw new Error()
      const current: HistoryStatus = await response.json()
      setStatus(current)
      if (current.active) {
        const queue = await fetch("/api/history/feedback?status=nuevo&limit=100")
        if (!queue.ok) throw new Error()
        const items: Feedback[] = await queue.json()
        setFeedback(items)
        setHasMore(items.length === 100)
      } else {
        setFeedback([])
        setHasMore(false)
      }
      setError("")
    } catch {
      setError("No se pudo consultar el estado del historial.")
    }
  }, [])

  useEffect(() => {
    void Promise.resolve().then(refresh)
  }, [refresh])

  async function review() {
    if (!selected || !answer.trim() || !confirmedError || !confirmedSafe) return
    setSaving(true)
    try {
      const response = await fetch(`/api/history/feedback/${encodeURIComponent(selected.feedback_id)}/review`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ conversation_id: selected.conversation_id, expected_answer: answer, confirmed_error: true, confirmed_no_sensitive_data: true }),
      })
      if (!response.ok) throw new Error()
      setSelected(null)
      setAnswer("")
      setConfirmedError(false)
      setConfirmedSafe(false)
      await refresh()
      toast.success("Aviso revisado")
    } catch {
      toast.error("No se pudo guardar la revisión")
    } finally {
      setSaving(false)
    }
  }

  async function openOriginal() {
    if (!selected) return
    try {
      await openConversation(selected.conversation_id)
      setSelected(null)
      router.push("/")
    } catch {
      toast.error("No se pudo abrir la conversación original")
    }
  }

  async function loadMore() {
    try {
      const response = await fetch(`/api/history/feedback?status=nuevo&limit=100&offset=${feedback.length}`)
      if (!response.ok) throw new Error()
      const items: Feedback[] = await response.json()
      setFeedback((current) => [...current, ...items])
      setHasMore(items.length === 100)
    } catch {
      toast.error("No se pudieron cargar más avisos")
    }
  }

  return (
    <section aria-label="Historial y revisión" className="mt-6 flex flex-col gap-4">
      <Card>
        <CardHeader><CardTitle>Historial</CardTitle><CardDescription>Almacenamiento y revisión local</CardDescription></CardHeader>
        <CardContent className="flex flex-col gap-3">
          {error ? <p role="alert">{error}</p> : null}
          {status ? <div className="flex flex-wrap gap-x-6 gap-y-1 text-sm"><span>{status.active ? "Activo" : "Desactivado"}</span><span>Retención: {status.retention_days} días</span><span>Guardados pendientes: {status.pending}</span></div> : null}
          {status?.failures.length ? <div><p className="font-medium">Últimos fallos de guardado</p><ul>{status.failures.map((failure, index) => <li className="break-all text-sm text-muted-foreground" key={`${failure.request_id}-${index}`}>{failure.request_id}: {failure.error}</li>)}</ul></div> : null}
          <div><Button onClick={() => void refresh()} size="sm" variant="outline">Actualizar</Button></div>
        </CardContent>
      </Card>
      {status?.active ? <Card>
        <CardHeader><CardTitle>Avisos pendientes</CardTitle><CardDescription>Revisa cada aviso antes de exportarlo.</CardDescription></CardHeader>
        <CardContent className="flex flex-col gap-3">
          {feedback.length === 0 ? <p className="text-muted-foreground">No hay avisos pendientes.</p> : <ul className="flex flex-col gap-2">{feedback.map((item) => <li className="flex items-center gap-3 border-b pb-2" key={item.feedback_id}><div className="min-w-0 flex-1"><p className="break-words">{item.comment || "Sin comentario"}</p><p className="text-xs text-muted-foreground">{new Date(item.created_at).toLocaleString("es-ES")}</p></div><Button onClick={() => { setAnswer(""); setConfirmedError(false); setConfirmedSafe(false); setSelected(item) }} size="sm" variant="outline">Revisar</Button></li>)}</ul>}
          {hasMore ? <div><Button onClick={() => void loadMore()} size="sm" variant="ghost">Cargar más avisos</Button></div> : null}
          <div><a className={buttonVariants({ variant: "outline", size: "sm" })} href="/api/history/feedback/export" download="feedback-revisado.jsonl">Exportar revisados</a></div>
        </CardContent>
      </Card> : null}
      <Dialog open={selected !== null} onOpenChange={(open) => { if (!open) setSelected(null) }}>
        <DialogContent>
          <DialogHeader><DialogTitle>Revisar aviso</DialogTitle><DialogDescription>Comprueba la respuesta original y elimina los datos sensibles antes de aprobar.</DialogDescription></DialogHeader>
          {selected ? <div className="flex max-h-[55vh] flex-col gap-3 overflow-y-auto">
            <p className="text-sm">{selected.comment || "Sin comentario"}</p>
            <p className="break-all text-xs text-muted-foreground">Consulta: {selected.request_id} · Conversación: {selected.conversation_id}</p>
            <div><Button disabled={busy} onClick={() => void openOriginal()} size="sm" variant="outline">Abrir conversación original</Button></div>
            {Object.keys(selected.trace).some((key) => key !== "request_id" && key !== "conversation_id") ? <pre className="max-h-40 overflow-auto rounded-md bg-muted p-3 text-xs whitespace-pre-wrap break-words">{JSON.stringify(selected.trace, null, 2)}</pre> : <p className="text-sm text-muted-foreground">El aviso no incluye contexto. Consulta la conversación en el historial antes de revisarlo.</p>}
            <div className="flex flex-col gap-2"><Label htmlFor="expected-answer">Respuesta esperada</Label><Textarea id="expected-answer" maxLength={4000} value={answer} onChange={(event) => setAnswer(event.target.value)} /></div>
            <label className="flex items-start gap-2 text-sm"><input type="checkbox" checked={confirmedError} onChange={(event) => setConfirmedError(event.target.checked)} /><span>He comprobado que hay un fallo real.</span></label>
            <label className="flex items-start gap-2 text-sm"><input type="checkbox" checked={confirmedSafe} onChange={(event) => setConfirmedSafe(event.target.checked)} /><span>He comprobado que el aviso y la respuesta esperada no contienen datos sensibles.</span></label>
          </div> : null}
          <DialogFooter><Button disabled={saving || !answer.trim() || !confirmedError || !confirmedSafe} onClick={() => void review()}>Marcar revisado</Button></DialogFooter>
        </DialogContent>
      </Dialog>
    </section>
  )
}
