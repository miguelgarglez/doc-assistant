"use client"

import {
  AlertCircleIcon,
  CheckIcon,
  FileTextIcon,
  ImageIcon,
  XIcon,
} from "lucide-react"
import type { ComponentProps, HTMLAttributes } from "react"
import { createContext, useContext, useMemo } from "react"

import { Spinner } from "@/components/ui/spinner"
import { cn } from "@/lib/utils"

export type AttachmentStatus = "uploading" | "processing" | "done" | "error"

export type AttachmentData = {
  id: string
  filename: string
  mediaType: string
  url?: string
  status?: AttachmentStatus
  /** 0 to 100 while status is "uploading". */
  progress?: number
  detail?: string
}

const AttachmentContext = createContext<{ data: AttachmentData; onRemove?: () => void } | null>(null)

const useAttachment = () => {
  const ctx = useContext(AttachmentContext)
  if (!ctx) throw new Error("Attachment parts need an Attachment parent")
  return ctx
}

export const Attachments = ({ className, ...props }: HTMLAttributes<HTMLUListElement>) => (
  <ul className={cn("flex flex-wrap items-center gap-1.5", className)} {...props} />
)

export type AttachmentProps = HTMLAttributes<HTMLLIElement> & {
  data: AttachmentData
  onRemove?: () => void
}

export const Attachment = ({ data, onRemove, className, children, ...props }: AttachmentProps) => {
  const value = useMemo(() => ({ data, onRemove }), [data, onRemove])
  return (
    <AttachmentContext.Provider value={value}>
      <li
        className={cn(
          "relative flex h-8 max-w-60 items-center gap-1.5 overflow-hidden rounded-lg border border-border bg-muted/50 pr-1 pl-1.5 text-xs",
          data.status === "error" && "border-destructive/40 bg-destructive/5",
          className
        )}
        data-status={data.status ?? "done"}
        {...props}
      >
        {children}
        {data.status === "uploading" ? (
          <span
            aria-hidden
            className="absolute inset-x-0 bottom-0 h-0.5 origin-left bg-primary transition-transform duration-150 ease-linear"
            style={{ transform: `scaleX(${(data.progress ?? 0) / 100})` }}
          />
        ) : null}
      </li>
    </AttachmentContext.Provider>
  )
}

export const AttachmentPreview = ({ className, ...props }: HTMLAttributes<HTMLSpanElement>) => {
  const { data } = useAttachment()
  const isImage = data.mediaType.startsWith("image/")
  return (
    <span
      className={cn("flex size-5 shrink-0 items-center justify-center overflow-hidden rounded bg-background text-muted-foreground", className)}
      {...props}
    >
      {isImage && data.url ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img alt="" className="size-full object-cover" src={data.url} />
      ) : isImage ? (
        <ImageIcon className="size-3.5" />
      ) : (
        <FileTextIcon className="size-3.5" />
      )}
    </span>
  )
}

const statusText: Record<AttachmentStatus, (data: AttachmentData) => string> = {
  uploading: (data) => `${data.progress ?? 0}%`,
  processing: () => "Procesando",
  done: () => "Listo",
  error: (data) => data.detail ?? "Error",
}

export const AttachmentInfo = ({ className, ...props }: HTMLAttributes<HTMLSpanElement>) => {
  const { data } = useAttachment()
  return (
    <span className={cn("flex min-w-0 flex-1 items-baseline gap-1.5", className)} {...props}>
      <span className="truncate font-medium">{data.filename}</span>
      {data.status ? (
        <span className={cn("shrink-0 tabular-nums text-muted-foreground", data.status === "error" && "text-destructive")}>
          {statusText[data.status](data)}
        </span>
      ) : null}
    </span>
  )
}

export const AttachmentStatusIcon = () => {
  const { data } = useAttachment()
  if (data.status === "uploading" || data.status === "processing") return <Spinner className="size-3.5 shrink-0 text-muted-foreground" />
  if (data.status === "done") return <CheckIcon className="size-3.5 shrink-0 text-[var(--ok-fg)]" />
  if (data.status === "error") return <AlertCircleIcon className="size-3.5 shrink-0 text-destructive" />
  return null
}

export const AttachmentRemove = ({
  label,
  className,
  ...props
}: Omit<ComponentProps<"button">, "onClick"> & { label?: string }) => {
  const { data, onRemove } = useAttachment()
  if (!onRemove) return null
  return (
    <button
      aria-label={label ?? `Quitar ${data.filename}`}
      className={cn(
        "flex size-5 shrink-0 cursor-pointer items-center justify-center rounded text-muted-foreground transition-colors hover:bg-background hover:text-foreground focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none",
        className
      )}
      onClick={onRemove}
      type="button"
      {...props}
    >
      <XIcon className="size-3.5" />
    </button>
  )
}
