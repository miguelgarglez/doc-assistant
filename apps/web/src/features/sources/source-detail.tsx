"use client"

import { ChevronLeftIcon, ChevronRightIcon, Trash2Icon, XIcon } from "lucide-react"
import { useEffect, useState } from "react"

import { StatusBadge } from "@/features/sources/status-badge"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { invoiceImageUrl, sourcePageUrl } from "@/lib/api/source-url"
import type { InvoiceListItem, Source, SourceChunk } from "@/lib/api/types"
import { displayField, formatAmountEs } from "@/lib/domain/format-amount"
import { cn } from "@/lib/utils"

type Tab = "fragments" | "page"

function useFetched<T>(url: string | null): { data: T | null; loading: boolean } {
  const [state, setState] = useState<{ url: string | null; data: T | null }>({ url: null, data: null })
  useEffect(() => {
    if (!url) return
    const controller = new AbortController()
    fetch(url, { signal: controller.signal, cache: "no-store" })
      .then((response) => (response.ok ? (response.json() as Promise<T>) : null))
      .then((data) => setState({ url, data }))
      .catch(() => {
        if (!controller.signal.aborted) setState({ url, data: null })
      })
    return () => controller.abort()
  }, [url])
  return { data: state.url === url ? state.data : null, loading: url !== null && state.url !== url }
}

const INVOICE_FIELDS: readonly [keyof InvoiceListItem, string, "text" | "amount"][] = [
  ["numero", "Número", "text"],
  ["fecha_emision", "Fecha de emisión", "text"],
  ["fecha_vencimiento", "Vencimiento", "text"],
  ["emisor", "Emisor", "text"],
  ["nif_emisor", "NIF emisor", "text"],
  ["cliente", "Cliente", "text"],
  ["nif_cliente", "NIF cliente", "text"],
  ["base_imponible_total", "Base imponible", "amount"],
  ["cuota_iva_total", "IVA", "amount"],
  ["irpf_importe", "IRPF", "amount"],
  ["importe_total", "Total", "amount"],
  ["iban", "IBAN", "text"],
]

type SourceDetailProps = {
  source: Source
  onClose: () => void
  onRemove: () => void
  className?: string
}

export function SourceDetail({ source, onClose, onRemove, className }: SourceDetailProps) {
  const isInvoice = source.kind === "invoice"
  const [tab, setTab] = useState<Tab>("fragments")
  const [page, setPage] = useState(1)
  const chunks = useFetched<SourceChunk[]>(isInvoice ? null : `/api/sources/${encodeURIComponent(source.id)}/chunks`)
  const invoices = useFetched<InvoiceListItem[]>(isInvoice ? "/api/invoices" : null)
  const invoice = invoices.data?.find((item) => item.numero === source.name) ?? null
  const pageCount = Math.max(source.n_pages, 0)
  const safePage = Math.min(Math.max(page, 1), Math.max(pageCount, 1))
  const imageSrc = isInvoice ? invoiceImageUrl(source.name) : pageCount > 0 ? sourcePageUrl(source.id, safePage) : null

  return (
    <section
      aria-label={`Detalle de ${source.title ?? source.name}`}
      className={cn("flex h-full min-h-0 flex-col bg-card", className)}
      data-testid="source-detail"
    >
      <header className="flex shrink-0 items-start gap-2 border-b border-border p-3">
        <div className="min-w-0 flex-1">
          <h2 className="truncate font-heading text-sm font-semibold">{source.title ?? source.name}</h2>
          <p className="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-muted-foreground">
            <span className="font-mono">{source.name}</span>
            <StatusBadge status={source.status} />
          </p>
        </div>
        <Button aria-label={`Quitar ${source.name} del índice`} data-testid="remove-source" onClick={onRemove} size="icon-sm" type="button" variant="ghost">
          <Trash2Icon />
        </Button>
        <Button aria-label="Cerrar detalle" onClick={onClose} size="icon-sm" type="button" variant="ghost">
          <XIcon />
        </Button>
      </header>

      <div className="shrink-0 border-b border-border px-3 py-2 text-xs text-muted-foreground">
        {source.n_pages} {source.n_pages === 1 ? "página" : "páginas"} · {source.n_chunks}{" "}
        {source.n_chunks === 1 ? "fragmento" : "fragmentos"}
        {source.status_detail ? <p className="mt-1 text-foreground">{source.status_detail}</p> : null}
      </div>

      {!isInvoice ? (
        <div className="flex shrink-0 gap-1 border-b border-border p-1.5" role="group" aria-label="Vista">
          {(
            [
              ["fragments", "Fragmentos"],
              ["page", "Página"],
            ] as const
          ).map(([id, label]) => (
            <Button
              aria-pressed={tab === id}
              key={id}
              onClick={() => setTab(id)}
              size="sm"
              type="button"
              variant={tab === id ? "secondary" : "ghost"}
            >
              {label}
            </Button>
          ))}
        </div>
      ) : null}

      <div className="min-h-0 flex-1 overflow-y-auto p-3">
        {isInvoice ? (
          <div className="flex flex-col gap-4">
            {invoices.loading ? (
              <Skeleton className="h-40 w-full" />
            ) : invoice ? (
              <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1.5 text-sm" data-testid="invoice-fields">
                {INVOICE_FIELDS.map(([key, label, kind]) => (
                  <div className="contents" key={key}>
                    <dt className="text-muted-foreground">{label}</dt>
                    <dd className="text-right tabular-nums">
                      {kind === "amount" ? formatAmountEs(invoice[key] as string | null | undefined) : displayField(invoice[key] as string | null | undefined)}
                    </dd>
                  </div>
                ))}
              </dl>
            ) : (
              <p className="text-sm text-muted-foreground">No hay datos extraídos para esta factura.</p>
            )}
            {invoice?.motivo ? <p className="rounded-md bg-[var(--review-bg)] p-2 text-xs text-[var(--review-fg)]">{invoice.motivo}</p> : null}
            {imageSrc ? <PageImage alt={`Imagen de la factura ${source.name}`} src={imageSrc} /> : null}
          </div>
        ) : tab === "fragments" ? (
          chunks.loading ? (
            <div className="flex flex-col gap-2">
              <Skeleton className="h-16 w-full" />
              <Skeleton className="h-16 w-full" />
            </div>
          ) : (
            <ol className="flex flex-col gap-2" data-testid="chunk-list">
              {(chunks.data ?? []).map((chunk) => (
                <li className="rounded-lg border border-border p-2.5" key={chunk.chunk_id}>
                  <p className="mb-1 font-mono text-[0.6875rem] text-muted-foreground">
                    Sección {chunk.section}
                    {chunk.pages.length > 0 ? ` · p. ${chunk.pages.join(", ")}` : ""}
                  </p>
                  <p className="line-clamp-6 text-sm leading-relaxed whitespace-pre-wrap">{chunk.text}</p>
                </li>
              ))}
              {chunks.data && chunks.data.length === 0 ? (
                <li className="text-sm text-muted-foreground">Sin fragmentos indexados.</li>
              ) : null}
            </ol>
          )
        ) : imageSrc ? (
          <div className="flex flex-col gap-2">
            <div className="flex items-center justify-between">
              <Button aria-label="Página anterior" disabled={safePage <= 1} onClick={() => setPage(safePage - 1)} size="icon-sm" type="button" variant="outline">
                <ChevronLeftIcon />
              </Button>
              <span className="text-xs tabular-nums text-muted-foreground">
                Página {safePage} de {pageCount}
              </span>
              <Button aria-label="Página siguiente" disabled={safePage >= pageCount} onClick={() => setPage(safePage + 1)} size="icon-sm" type="button" variant="outline">
                <ChevronRightIcon />
              </Button>
            </div>
            <PageImage alt={`Página ${safePage} de ${source.name}`} src={imageSrc} />
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">Esta fuente no tiene páginas renderizadas.</p>
        )}
      </div>
    </section>
  )
}

function PageImage({ alt, src }: { alt: string; src: string }) {
  return (
    // eslint-disable-next-line @next/next/no-img-element -- PNG dinámico del proxy
    <img alt={alt} className="h-auto w-full rounded-md border border-border bg-muted object-contain object-top" src={src} />
  )
}
