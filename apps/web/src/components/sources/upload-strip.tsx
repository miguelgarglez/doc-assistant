"use client"

import { FileTextIcon, ImageIcon, RotateCcwIcon, UploadCloudIcon, XIcon } from "lucide-react"
import { useRef } from "react"

import { useUploads, type UploadItem } from "@/components/providers/uploads-provider"
import { Button } from "@/components/ui/button"
import { Spinner } from "@/components/ui/spinner"
import { cn } from "@/lib/utils"

const ACCEPT = ".pdf,application/pdf,image/png,image/jpeg"

function statusText(item: UploadItem): string {
  switch (item.status) {
    case "queued":
      return "En cola"
    case "uploading":
      return `Subiendo ${item.progress}%`
    case "processing":
      return item.kind === "invoice" ? "Leyendo la factura (OCR)…" : "Indexando…"
    case "done":
      return item.detail ?? "Listo"
    case "error":
      return item.detail ?? "Error"
  }
}

function Row({ item }: { item: UploadItem }) {
  const { retry, cancel, dismiss } = useUploads()
  const busy = item.status === "uploading" || item.status === "processing"
  const Icon = item.kind === "invoice" ? ImageIcon : FileTextIcon
  return (
    <li
      className="relative flex items-center gap-3 overflow-hidden rounded-lg border border-border bg-card px-3 py-2"
      data-status={item.status}
      data-testid="upload-row"
    >
      <Icon aria-hidden className="size-4 shrink-0 text-muted-foreground" />
      <span className="min-w-0 flex-1 truncate text-sm font-medium">{item.name}</span>
      <span
        className={cn(
          "flex shrink-0 items-center gap-1.5 text-xs tabular-nums text-muted-foreground",
          item.status === "error" && "text-destructive",
          item.status === "done" && "text-[var(--ok-fg)]"
        )}
        role={item.status === "error" ? "alert" : "status"}
      >
        {item.status === "processing" ? <Spinner className="size-3.5" /> : null}
        {statusText(item)}
      </span>
      {item.status === "error" && item.detail !== "Subida cancelada." && !item.detail?.startsWith("Solo se admiten") ? (
        <Button aria-label={`Reintentar ${item.name}`} onClick={() => retry(item.id)} size="icon-xs" type="button" variant="ghost">
          <RotateCcwIcon />
        </Button>
      ) : null}
      <Button
        aria-label={busy ? `Cancelar ${item.name}` : `Quitar ${item.name} de la lista`}
        onClick={() => (busy ? cancel(item.id) : dismiss(item.id))}
        size="icon-xs"
        type="button"
        variant="ghost"
      >
        <XIcon />
      </Button>
      {item.status === "uploading" ? (
        <span
          aria-hidden
          className="absolute inset-x-0 bottom-0 h-0.5 origin-left bg-primary transition-transform duration-150 ease-linear"
          style={{ transform: `scaleX(${item.progress / 100})` }}
        />
      ) : null}
    </li>
  )
}

/** Compact upload target plus the queue. Files dropped anywhere in the window land here too. */
export function UploadStrip() {
  const { items, enqueue } = useUploads()
  const inputRef = useRef<HTMLInputElement>(null)
  const visible = items.filter((item) => item.origin === "sources" || item.status !== "done").slice(-5)
  return (
    <div className="flex flex-col gap-2" data-testid="upload-strip">
      <input
        accept={ACCEPT}
        aria-label="Elegir archivos para añadir como fuentes"
        className="hidden"
        data-testid="sources-file-input"
        multiple
        onChange={(event) => {
          const files = Array.from(event.currentTarget.files ?? [])
          event.currentTarget.value = ""
          if (files.length > 0) enqueue(files, "sources")
        }}
        ref={inputRef}
        tabIndex={-1}
        type="file"
      />
      <button
        className="flex w-full cursor-pointer items-center gap-3 rounded-xl border border-dashed border-border bg-card/60 px-4 py-3 text-left transition-[background-color,border-color] duration-150 ease-[var(--ease-out)] outline-none hover:border-primary/60 hover:bg-card focus-visible:ring-3 focus-visible:ring-ring/50"
        data-testid="upload-trigger"
        onClick={() => inputRef.current?.click()}
        type="button"
      >
        <span className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-secondary text-secondary-foreground">
          <UploadCloudIcon className="size-5" />
        </span>
        <span className="flex min-w-0 flex-col">
          <span className="text-sm font-medium">Añadir fuentes</span>
          <span className="text-xs text-muted-foreground sm:truncate">
            PDF para documentos, PNG o JPG para facturas.
            <span className="hidden sm:inline"> También puedes soltarlos en cualquier parte de la ventana.</span>
          </span>
        </span>
      </button>
      {visible.length > 0 ? (
        <ul aria-label="Archivos en proceso" className="flex flex-col gap-1.5">
          {visible.map((item) => (
            <Row item={item} key={item.id} />
          ))}
        </ul>
      ) : null}
    </div>
  )
}
