"use client"

import { useEffect, useState } from "react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { copyText } from "@/lib/clipboard"

const PAGE_SIZE = 10

type RequestItem = {
  request_id: string
  conversation_id: string
  created_at: string
  kind: string | null
  status: string | null
  elapsed_s: number | null
}
type PageState = { kind: "loading" } | { kind: "error" } | { kind: "ready"; items: RequestItem[] }

const labels: Record<string, string> = {
  answer: "Respuesta", clarification: "Aclaración", refusal: "Rechazo", error: "Error",
  completed: "Completada", interrupted: "Interrumpida", pending: "Pendiente",
}

export function RecentRequests({ failures }: { failures: { request_id: string; error: string }[] }) {
  const [page, setPage] = useState(0)
  const [retry, setRetry] = useState(0)
  const [state, setState] = useState<PageState>({ kind: "loading" })
  useEffect(() => {
    const controller = new AbortController()
    void fetch(`/api/history/requests?limit=${PAGE_SIZE + 1}&offset=${page * PAGE_SIZE}`, { signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) throw new Error("request failed")
        return response.json() as Promise<RequestItem[]>
      })
      .then((items) => setState({ kind: "ready", items }))
      .catch(() => { if (!controller.signal.aborted) setState({ kind: "error" }) })
    return () => controller.abort()
  }, [page, retry])

  function go(next: number) {
    setState({ kind: "loading" })
    setPage(next)
  }
  async function copy(id: string) {
    if (await copyText(id)) toast.success("Identificador copiado")
    else toast.error("No se pudo copiar el identificador")
  }

  return <Card>
    <CardHeader><CardTitle>Peticiones recientes</CardTitle><CardDescription>Consultas guardadas en este equipo. Los fallos de escritura pendientes aparecen en el estado del historial.</CardDescription></CardHeader>
    <CardContent className="flex flex-col gap-3">
      {state.kind === "loading" ? <p role="status">Cargando peticiones…</p> : null}
      {state.kind === "error" ? <div role="alert">No se pudieron cargar las peticiones. <Button size="sm" variant="outline" onClick={() => { setState({ kind: "loading" }); setRetry((n) => n + 1) }}>Reintentar</Button></div> : null}
      {state.kind === "ready" && state.items.length === 0 ? <p>No hay peticiones guardadas.</p> : null}
      {state.kind === "ready" && state.items.length > 0 ? <Table>
        <TableHeader><TableRow><TableHead>Hora</TableHead><TableHead>Tipo</TableHead><TableHead>Estado</TableHead><TableHead>Latencia</TableHead><TableHead>Identificador</TableHead><TableHead>Guardado</TableHead></TableRow></TableHeader>
        <TableBody>{state.items.slice(0, PAGE_SIZE).map((item) => {
          const failure = failures.find((entry) => entry.request_id === item.request_id)
          return <TableRow key={item.request_id}>
            <TableCell>{new Date(item.created_at).toLocaleString("es-ES")}</TableCell>
            <TableCell>{item.kind ? labels[item.kind] ?? item.kind : "Consulta"}</TableCell>
            <TableCell>{item.status ? labels[item.status] ?? item.status : "Sin dato"}</TableCell>
            <TableCell>{item.elapsed_s == null ? "—" : `${item.elapsed_s.toLocaleString("es-ES", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} s`}</TableCell>
            <TableCell><Button variant="ghost" size="sm" onClick={() => void copy(item.request_id)} aria-label={`Copiar identificador ${item.request_id}`}>{item.request_id}</Button></TableCell>
            <TableCell>{failure ? `Reintentado: ${failure.error}` : "Guardada"}</TableCell>
          </TableRow>
        })}</TableBody>
      </Table> : null}
      <div className="flex items-center gap-3"><Button size="sm" variant="outline" disabled={page === 0 || state.kind === "loading"} onClick={() => go(page - 1)}>Anterior</Button><span className="text-sm">Página {page + 1}</span><Button size="sm" variant="outline" disabled={state.kind !== "ready" || state.items.length <= PAGE_SIZE} onClick={() => go(page + 1)}>Siguiente</Button></div>
    </CardContent>
  </Card>
}
