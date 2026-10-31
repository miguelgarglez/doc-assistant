"use client"

import { useId, useRef, useState } from "react"
import { UploadIcon } from "lucide-react"

import { AskErrorNotice } from "@/components/domain/AskErrorNotice"
import { Button } from "@/components/ui/button"
import { Progress } from "@/components/ui/progress"
import { Skeleton } from "@/components/ui/skeleton"
import type { ErrorBody } from "@/lib/api/types"
import { cn } from "@/lib/utils"

export type UploadDropzoneProps = {
  accept: string
  acceptLabel: string
  title: string
  description: string
  disabled?: boolean
  uploading?: boolean
  progress?: number | null
  error?: ErrorBody | null
  compact?: boolean
  onFile: (file: File) => void
  onCancel?: () => void
  onRetry?: () => void
  "data-testid"?: string
}

export function UploadDropzone({
  accept,
  acceptLabel,
  title,
  description,
  disabled = false,
  uploading = false,
  progress = null,
  error = null,
  compact = false,
  onFile,
  onRetry,
  onCancel,
  "data-testid": testId = "upload-dropzone",
}: UploadDropzoneProps) {
  const inputId = useId()
  const inputRef = useRef<HTMLInputElement>(null)
  const [active, setActive] = useState(false)
  const busy = disabled || uploading

  function takeFile(fileList: FileList | null) {
    const file = fileList?.[0]
    if (!file || busy) {
      return
    }
    onFile(file)
  }

  return (
    <div className="flex flex-col gap-3" data-testid={testId}>
      <div className="flex flex-col gap-1">
        <h3
          className={
            compact
              ? "text-sm font-medium text-foreground"
              : "text-base font-medium text-foreground"
          }
        >
          {title}
        </h3>
        <p className="text-sm leading-relaxed text-muted-foreground">
          {description}
        </p>
      </div>

      <div
        className={cn(
          "flex flex-col items-center gap-3 rounded-lg border border-dashed px-4 text-center transition-[border-color,background-color] duration-[var(--duration-fast)] ease-[var(--ease-out)]",
          compact ? "py-5" : "px-6 py-10",
          active ? "border-primary bg-muted/60" : "border-border bg-card",
          busy ? "pointer-events-none opacity-70" : null
        )}
        onDragEnter={(event) => {
          event.preventDefault()
          if (!busy) setActive(true)
        }}
        onDragOver={(event) => {
          event.preventDefault()
          if (!busy) setActive(true)
        }}
        onDragLeave={(event) => {
          event.preventDefault()
          setActive(false)
        }}
        onDrop={(event) => {
          event.preventDefault()
          setActive(false)
          takeFile(event.dataTransfer.files)
        }}
      >
        {uploading ? (
          <div
            className="flex w-full flex-col items-center gap-3"
            role="status"
            aria-live="polite"
            data-testid={`${testId}-loading`}
          >
            {progress == null ? (
              <>
                <Skeleton
                  className={
                    compact ? "h-8 w-8 rounded-full" : "h-10 w-10 rounded-full"
                  }
                />
                <Skeleton className="h-4 w-40" />
              </>
            ) : (
              <Progress
                value={progress}
                label="Subiendo archivo"
                className="w-full max-w-xs"
                data-testid={`${testId}-progress`}
              />
            )}
            <p className="sr-only">Subiendo archivo…</p>
          </div>
        ) : (
          <>
            <UploadIcon className="size-5 text-muted-foreground" />
            <p className="text-sm text-muted-foreground">
              Arrastra un archivo aquí o elige desde el disco.
            </p>
            <p className="font-mono text-xs text-muted-foreground">
              {acceptLabel}
            </p>
            <Button
              type="button"
              variant="outline"
              size="sm"
              disabled={busy}
              onClick={() => inputRef.current?.click()}
              className="active:scale-[0.97] motion-reduce:active:scale-100"
            >
              Elegir archivo
            </Button>
          </>
        )}
        <input
          ref={inputRef}
          id={inputId}
          type="file"
          accept={accept}
          className="sr-only"
          disabled={busy}
          aria-label={title}
          onChange={(event) => {
            takeFile(event.target.files)
            event.target.value = ""
          }}
        />
      </div>

      {uploading && onCancel ? <Button type="button" variant="outline" onClick={onCancel}>Cancelar subida</Button> : null}
      {error ? <AskErrorNotice error={error} onRetry={onRetry} /> : null}
    </div>
  )
}
