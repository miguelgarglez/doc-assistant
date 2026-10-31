"use client"

import { useEffect, useState } from "react"
import { DocumentUploadPanel } from "@/components/domain/DocumentUploadPanel"
import { InvoicesWorkspace } from "@/components/domain/InvoicesWorkspace"
import { useDocumentUpload } from "@/hooks/use-document-upload"
import { useInvoices } from "@/hooks/use-invoices"
import { sourcePageUrl } from "@/lib/api/source-url"

type Source = { id: string; kind: "pdf" | "invoice"; name: string; title: string | null; n_pages: number; n_chunks: number; sections: { section: string; heading: string | null; pages: number[] }[]; added_at: string | null; status: string; status_detail: string | null }
type Chunk = { chunk_id: string; section: string; pages: number[]; text: string }

export default function SourcesPage() {
  const document = useDocumentUpload()
  const invoices = useInvoices()
  const [sources, setSources] = useState<Source[]>([])
  const [selected, setSelected] = useState<Source | null>(null)
  const [page, setPage] = useState(1)
  const [error, setError] = useState("")
  const [chunks, setChunks] = useState<Chunk[]>([])
  useEffect(() => {
    const controller = new AbortController()
    fetch("/api/sources", { signal: controller.signal }).then((response) => {
      if (!response.ok) throw new Error("No se pudieron cargar las fuentes.")
      return response.json() as Promise<Source[]>
    }).then(setSources).catch((err: unknown) => { if (!controller.signal.aborted) setError(err instanceof Error ? err.message : "Error al cargar las fuentes.") })
    return () => controller.abort()
  }, [document.status.kind, invoices.uploadStatus.kind])
  useEffect(() => {
    if (!selected) return
    const controller = new AbortController()
    fetch(`/api/sources/${encodeURIComponent(selected.id)}/chunks`, { signal: controller.signal })
      .then((response) => response.ok ? response.json() : [])
      .then(setChunks)
      .catch(() => {})
    return () => controller.abort()
  }, [selected])
  return <main className="mx-auto flex w-full max-w-6xl flex-col gap-8 px-4 py-8 sm:px-6">
    <div><h1 className="font-heading text-3xl font-semibold">Fuentes</h1><p className="mt-2 text-muted-foreground">Añade documentos y revisa su contenido indexado.</p></div>
    <div className="grid gap-6 lg:grid-cols-2"><DocumentUploadPanel api={document} /><InvoicesWorkspace api={invoices} /></div>
    <section aria-labelledby="sources-title" className="flex flex-col gap-4">
      <h2 id="sources-title" className="font-heading text-xl font-medium">Documentos indexados</h2>
      {error ? <p role="alert">{error}</p> : null}
      {!error && sources.length === 0 ? <p className="text-muted-foreground">Todavía no hay fuentes indexadas.</p> : null}
      <div className="grid gap-4 lg:grid-cols-2"><ul className="flex flex-col gap-2">
        {sources.map((source) => <li key={source.id}><button type="button" onClick={() => { setSelected(source); setPage(1) }} aria-pressed={selected?.id === source.id} className="w-full rounded-lg border border-border bg-card p-4 text-left hover:bg-muted"><span className="block font-medium">{source.title || source.name}</span><span className="mt-1 block text-sm text-muted-foreground">{source.kind === "pdf" ? "PDF" : "Factura"} · {source.n_pages} páginas · {source.n_chunks} fragmentos · {source.status === "indexed" ? "Indexada" : "Revisar"}{source.added_at ? ` · ${new Date(source.added_at).toLocaleDateString("es-ES")}` : ""}</span></button></li>)}
      </ul>{selected ? <article className="flex flex-col gap-3 rounded-lg border border-border bg-card p-4"><h3 className="font-heading text-lg font-medium">{selected.title || selected.name}</h3>{selected.status_detail ? <p>{selected.status_detail}</p> : null}
        <ul className="flex flex-col gap-1 text-sm">{selected.sections.map((section, index) => <li key={`${section.section}-${index}`}><button className="text-left underline" onClick={() => setPage(section.pages[0] ?? 1)}>{section.section} {section.heading} · p. {section.pages.join(", ")}</button></li>)}</ul>
        {chunks.map((chunk) => <details key={chunk.chunk_id} className="rounded-md border border-border p-3 text-sm"><summary className="cursor-pointer">Fragmento {chunk.section} · p. {chunk.pages.join(", ")}</summary><p className="mt-2 whitespace-pre-wrap">{chunk.text}</p></details>)}
        {selected.n_pages ? <><div className="flex items-center gap-3"><button disabled={page <= 1} onClick={() => setPage(page - 1)} className="underline disabled:opacity-50">Anterior</button><span>Página {page} de {selected.n_pages}</span><button disabled={page >= selected.n_pages} onClick={() => setPage(page + 1)} className="underline disabled:opacity-50">Siguiente</button></div>{/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={sourcePageUrl(selected.id, page)} alt={`Página ${page} de ${selected.name}`} className="max-h-[36rem] w-full object-contain" /></> : null}
      </article> : null}</div>
    </section>
  </main>
}
