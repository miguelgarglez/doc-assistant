"use client"

import { useEffect, useState } from "react"
import { Button } from "@/components/ui/button"
import { useTrace } from "@/components/system/trace-provider"

const pieces = [
  { id: "web", label: "Web", steps: ["route"] },
  { id: "proxy", label: "Proxy / BFF", steps: ["route"] },
  { id: "ai", label: "Servicio AI", steps: ["route", "meta", "invoices", "verify"] },
  { id: "embeddings", label: "Embeddings", steps: ["retrieve"] },
  { id: "sqlite", label: "Índice SQLite", steps: ["retrieve", "meta", "invoices"] },
  { id: "reranker", label: "Reranker", steps: ["rerank"] },
  { id: "llm", label: "LLM", steps: ["generate"] },
  { id: "ocr", label: "OCR", steps: [] },
] as const
type Health = { id: string; status: string; latency_ms: number | null; detail: string | null }

// El guard de administrador se aplicará aquí cuando exista autenticación.
export default function SystemPage() {
  const { steps } = useTrace()
  const [health, setHealth] = useState<Health[]>([])
  const [replay, setReplay] = useState<number | null>(null)
  useEffect(() => {
    const controller = new AbortController()
    fetch("/api/health/components", { signal: controller.signal }).then((response) => response.ok ? response.json() : null).then((data) => { if (data?.components) setHealth(data.components) }).catch(() => {})
    return () => controller.abort()
  }, [])
  useEffect(() => {
    if (replay === null) return
    if (replay >= steps.length - 1) return
    const timer = window.setTimeout(() => setReplay(replay + 1), 700)
    return () => window.clearTimeout(timer)
  }, [replay, steps.length])
  const active = replay === null ? steps.at(-1) : steps[replay]
  return <main className="mx-auto flex w-full max-w-6xl flex-col gap-8 px-4 py-8 sm:px-6">
    <div><h1 className="font-heading text-3xl font-semibold">Sistema</h1><p className="mt-2 text-muted-foreground">Piezas y recorrido de la última consulta.</p></div>
    <section aria-labelledby="architecture-heading" className="flex flex-col gap-4"><h2 id="architecture-heading" className="font-heading text-xl font-medium">Arquitectura</h2><p className="text-sm text-muted-foreground">Web → Proxy / BFF → Servicio AI → modelos e índice</p><div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">{pieces.map((piece) => {
      const state = health.find((item) => item.id === piece.id)
      const lit = active?.status === "running" && (piece.steps as readonly string[]).includes(active.id)
      return <article key={piece.id} className={`rounded-lg border bg-card p-4 ${lit ? "border-primary ring-2 ring-primary/30" : "border-border"}`}><h3 className="font-medium">{piece.label}</h3><p className="mt-2 text-sm text-muted-foreground">{state ? `${state.status} ${state.latency_ms === null ? "" : `· ${state.latency_ms} ms`}` : "Estado sin medir"}</p>{state?.detail ? <p className="mt-1 text-sm">{state.detail}</p> : null}</article>
    })}</div></section>
    <section aria-labelledby="trace-heading" className="flex flex-col gap-4"><div className="flex flex-wrap items-center justify-between gap-3"><h2 id="trace-heading" className="font-heading text-xl font-medium">Última petición</h2><Button variant="outline" disabled={!steps.length} onClick={() => setReplay(0)}>Reproducir</Button></div>{steps.length ? <ol className="flex flex-col gap-2">{steps.map((step, index) => <li key={index} className={`rounded-md border p-3 text-sm ${replay === index ? "border-primary bg-muted" : "border-border"}`}>{step.label} · {step.status === "done" ? "completado" : "en curso"}{step.elapsed_s !== undefined ? ` · ${step.elapsed_s.toFixed(2)} s` : ""}</li>)}</ol> : <p className="text-sm text-muted-foreground">Haz una consulta para ver su recorrido.</p>}</section>
  </main>
}
