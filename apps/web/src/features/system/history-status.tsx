"use client"

import { useCallback, useEffect, useState } from "react"
import Link from "next/link"
import { toast } from "sonner"
import { RecentRequests } from "@/features/system/recent-requests"
import { Button, buttonVariants } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Empty, EmptyDescription } from "@/components/ui/empty"
import { copyText } from "@/lib/clipboard"

type HistoryStatus = { active: boolean; enabled: boolean; initialization_error: string | null; retention_days: number; pending: number; failures: { request_id: string; error: string }[] }
type Feedback = { feedback_id: string; created_at: string; comment: string | null }

export function HistoryStatusPanel() {
  const [status, setStatus] = useState<HistoryStatus | null>(null)
  const [feedback, setFeedback] = useState<Feedback[]>([])
  const [error, setError] = useState("")
  const [revision, setRevision] = useState(0)
  const refresh = useCallback(async () => {
    try {
      const response = await fetch("/api/history/status")
      if (!response.ok) throw new Error()
      const current: HistoryStatus = await response.json()
      setStatus(current)
      if (current.active) {
        const queue = await fetch("/api/history/feedback?status=nuevo&limit=5")
        if (!queue.ok) throw new Error()
        setFeedback(await queue.json())
      } else setFeedback([])
      setError("")
      setRevision((current) => current + 1)
    } catch { setError("No se pudo consultar el estado del historial.") }
  }, [])
  async function copyFailure(id: string) {
    if (await copyText(id)) toast.success("Identificador copiado")
    else toast.error("No se pudo copiar el identificador")
  }
  useEffect(() => { void Promise.resolve().then(refresh) }, [refresh])
  return <section aria-label="Historial y revisión" className="mt-6 flex flex-col gap-4">
    <Card><CardHeader><CardTitle>Historial</CardTitle><CardDescription>Almacenamiento y revisión local</CardDescription></CardHeader>
      <CardContent className="flex flex-col gap-3">
        {error ? <p role="alert">{error}</p> : null}
        {status ? <div className="flex flex-wrap gap-x-6 gap-y-1 text-sm"><span>{status.active ? "Activo" : status.enabled ? "No disponible, reintentando" : "Desactivado"}</span><span>Retención: {status.retention_days} días</span><span>Guardados pendientes: {status.pending}</span></div> : <p role="status">Cargando estado…</p>}
        {status?.initialization_error ? <p className="text-sm">Error al abrir el almacén: {status.initialization_error}</p> : null}
        {status?.failures.length ? <div><p className="font-medium">Últimos fallos de guardado</p><ul>{status.failures.map((failure, index) => <li className="break-all text-sm text-muted-foreground" key={`${failure.request_id}-${index}`}><Button variant="ghost" size="sm" aria-label={`Copiar identificador ${failure.request_id}`} onClick={() => void copyFailure(failure.request_id)}>{failure.request_id}</Button>: {failure.error}</li>)}</ul></div> : null}
        <div><Button onClick={() => void refresh()} size="sm" variant="outline">Actualizar</Button></div>
      </CardContent></Card>
    {status?.active ? <RecentRequests failures={status.failures} revision={revision} /> : null}
    {status?.active ? <Card><CardHeader><CardTitle>Avisos pendientes</CardTitle><CardDescription>Revisa cada aviso antes de exportarlo.</CardDescription></CardHeader><CardContent className="flex flex-col gap-3">
      {feedback.length ? <ul className="flex flex-col gap-2">{feedback.map((item) => <li className="flex items-center gap-3 border-b pb-2" key={item.feedback_id}><div className="min-w-0 flex-1"><p className="break-words">{item.comment || "Sin comentario"}</p><p className="text-xs text-muted-foreground">{new Date(item.created_at).toLocaleString("es-ES")}</p></div><Link className={buttonVariants({ variant: "outline", size: "sm" })} href={`/revision?id=${encodeURIComponent(item.feedback_id)}`}>Revisar</Link></li>)}</ul> : <Empty><EmptyDescription>No hay avisos pendientes.</EmptyDescription></Empty>}
      <div><Link className={buttonVariants({ variant: "outline", size: "sm" })} href="/revision">Abrir cola de revisión</Link></div>
    </CardContent></Card> : null}
  </section>
}
