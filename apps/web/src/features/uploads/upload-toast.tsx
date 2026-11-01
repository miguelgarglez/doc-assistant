"use client"

import { AlertCircleIcon, CheckIcon, FileTextIcon, ImageIcon, InfoIcon, Loader2Icon, RotateCcwIcon, XIcon } from "lucide-react"
import { usePathname, useRouter } from "next/navigation"
import { useEffect, useState } from "react"
import { toast } from "sonner"

import { useUploads, type UploadItem } from "@/features/uploads/uploads-provider"
import { Button } from "@/components/ui/button"
import { isActive, summarizeUploads, uploadStatusText } from "@/features/uploads/status"
import { cn } from "@/lib/utils"

const TOAST_ID = "uploads"
const LINGER_MS = 12_000

function StatusIcon({ item }: { item: UploadItem }) {
  if (item.status === "done") {
    const Icon = item.duplicate ? InfoIcon : CheckIcon
    return <Icon aria-hidden className="size-4 text-[var(--ok-fg)]" />
  }
  if (item.status === "error") return <AlertCircleIcon aria-hidden className="size-4 text-destructive" />
  if (item.status === "processing") return <Loader2Icon aria-hidden className="size-4 animate-spin text-muted-foreground motion-reduce:animate-none" />
  const Icon = item.kind === "invoice" ? ImageIcon : FileTextIcon
  return <Icon aria-hidden className="size-4 text-muted-foreground" />
}

function Row({ item }: { item: UploadItem }) {
  const { retry, cancel, dismiss } = useUploads()
  const cancellable = item.status === "queued" || item.status === "uploading"
  return (
    <li
      className="relative flex items-center gap-2.5 px-3 py-2"
      data-status={item.status}
      data-testid="upload-row"
    >
      <StatusIcon item={item} />
      <div className="flex min-w-0 flex-1 flex-col">
        <span className="truncate text-sm font-medium">{item.name}</span>
        <span
          className={cn(
            "text-xs tabular-nums text-muted-foreground",
            item.status !== "error" && "truncate",
            item.status === "error" && "text-popover-foreground",
            item.status === "done" && !item.duplicate && "text-[var(--ok-fg)]"
          )}
          data-testid="upload-status"
          title={uploadStatusText(item)}
        >
          {uploadStatusText(item)}
        </span>
      </div>
      {item.status === "error" && item.retryable ? (
        <Button aria-label={`Reintentar ${item.name}`} onClick={() => retry(item.id)} size="xs" type="button" variant="outline">
          <RotateCcwIcon data-icon="inline-start" />
          Reintentar
        </Button>
      ) : null}
      {item.status === "error" ? (
        <Button aria-label={`Cerrar error de ${item.name}`} onClick={() => dismiss(item.id)} size="icon-xs" type="button" variant="ghost">
          <XIcon />
        </Button>
      ) : null}
      {cancellable ? (
        <Button aria-label={`Cancelar ${item.name}`} onClick={() => cancel(item.id)} size="icon-xs" type="button" variant="ghost">
          <XIcon />
        </Button>
      ) : null}
      {item.status === "uploading" ? (
        <>
          <progress className="sr-only" aria-label={`Subiendo ${item.name}`} value={item.progress} max={100} />
          <span
            aria-hidden
            className="absolute inset-x-3 bottom-0 h-0.5 origin-left rounded-full bg-primary transition-transform duration-150 ease-linear motion-reduce:transition-none"
            style={{ transform: `scaleX(${item.progress / 100})` }}
          />
        </>
      ) : null}
    </li>
  )
}

/** Live status of every file being added. Lives in the toast region, so it outlasts the dialog and page changes. */
export function UploadToastContent() {
  const { items, hideFinished } = useUploads()
  const router = useRouter()
  const pathname = usePathname()
  const [hovered, setHovered] = useState(false)
  const listed = items.filter((item) => !item.hidden).sort((a, b) => Number(b.status === "error") - Number(a.status === "error"))
  const summary = summarizeUploads(listed)
  const finished = summary.active === 0
  const calm = finished && summary.failed === 0

  useEffect(() => {
    if (!calm || hovered) return
    const timer = window.setTimeout(hideFinished, LINGER_MS)
    return () => window.clearTimeout(timer)
  }, [calm, hovered, hideFinished, listed.length])

  return (
    <section
      aria-label="Estado de las subidas"
      className="w-[min(26rem,calc(100vw-2rem))] overflow-hidden rounded-xl border border-border bg-popover text-popover-foreground shadow-lg"
      data-testid="upload-toast"
      onPointerEnter={() => setHovered(true)}
      onPointerLeave={() => setHovered(false)}
    >
      <header className="flex items-center gap-2 border-b border-border px-3 py-2">
        <h2 className="min-w-0 flex-1 truncate font-heading text-sm font-semibold" data-testid="upload-toast-title">
          {summary.title}
        </h2>
        {summary.done > 0 && !pathname.startsWith("/fuentes") ? (
          <Button data-testid="upload-toast-open" onClick={() => router.push("/fuentes")} size="xs" type="button" variant="secondary">
            Ver en Fuentes
          </Button>
        ) : null}
        {finished ? (
          <Button aria-label="Cerrar el aviso" data-testid="upload-toast-close" onClick={hideFinished} size="icon-xs" type="button" variant="ghost">
            <XIcon />
          </Button>
        ) : null}
      </header>
      <ul className="flex max-h-[min(15rem,calc(100dvh_-_12rem))] flex-col divide-y divide-border/60 overflow-y-auto" aria-live="polite">
        {listed.map((item) => (
          <Row item={item} key={item.id} />
        ))}
      </ul>
    </section>
  )
}

/** Keeps one persistent toast in step with the upload queue. */
export function UploadToast() {
  const { items } = useUploads()
  const open = items.some((item) => !item.hidden)
  const running = items.some((item) => !item.hidden && isActive(item))
  useEffect(() => {
    if (!open) {
      toast.dismiss(TOAST_ID)
      return
    }
    toast.custom(() => <UploadToastContent />, { id: TOAST_ID, duration: Number.POSITIVE_INFINITY, dismissible: !running })
  }, [open, running])
  return null
}
