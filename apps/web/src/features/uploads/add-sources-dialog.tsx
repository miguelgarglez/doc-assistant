"use client"

import { FileTextIcon, ImageIcon, UploadCloudIcon } from "lucide-react"
import { useRef, useState, type DragEvent } from "react"

import { useUploads } from "@/features/uploads/uploads-provider"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { cn } from "@/lib/utils"

export const ACCEPT = ".pdf,application/pdf,image/png,image/jpeg"

const hasFiles = (event: DragEvent) => Array.from(event.dataTransfer.types).includes("Files")

type AddSourcesDialogProps = {
  open: boolean
  onOpenChange: (open: boolean) => void
}

/** The big drop target. Choosing or dropping files starts the upload and closes the dialog; the toast takes over. */
export function AddSourcesDialog({ open, onOpenChange }: AddSourcesDialogProps) {
  const { enqueue } = useUploads()
  const inputRef = useRef<HTMLInputElement>(null)
  const [over, setOver] = useState(false)
  const depth = useRef(0)

  const take = (files: File[]) => {
    if (files.length === 0) return
    enqueue(files, "sources")
    onOpenChange(false)
  }

  const stop = (event: DragEvent) => {
    if (!hasFiles(event)) return false
    event.preventDefault()
    event.stopPropagation()
    return true
  }

  return (
    <Dialog onOpenChange={onOpenChange} open={open}>
      <DialogContent className="gap-4 sm:max-w-lg" data-testid="add-sources-dialog">
        <DialogHeader>
          <DialogTitle>Añadir fuentes</DialogTitle>
          <DialogDescription>Los documentos y las facturas se indexan para poder citarlos en las respuestas.</DialogDescription>
        </DialogHeader>
        <input
          accept={ACCEPT}
          aria-label="Elegir archivos para añadir como fuentes"
          className="hidden"
          data-testid="sources-file-input"
          multiple
          onChange={(event) => {
            const files = Array.from(event.currentTarget.files ?? [])
            event.currentTarget.value = ""
            take(files)
          }}
          ref={inputRef}
          tabIndex={-1}
          type="file"
        />
        <button
          className={cn(
            "flex w-full cursor-pointer flex-col items-center gap-3 rounded-xl border-2 border-dashed border-border bg-muted/40 px-6 py-10 text-center transition-[background-color,border-color,transform] duration-150 ease-[var(--ease-out)] outline-none focus-visible:border-primary focus-visible:ring-3 focus-visible:ring-ring/50 active:scale-[0.99] motion-reduce:transition-none [@media(hover:hover)]:hover:border-primary/60 [@media(hover:hover)]:hover:bg-muted/70",
            over && "border-primary bg-primary/10"
          )}
          data-over={over}
          data-testid="dropzone"
          onClick={() => inputRef.current?.click()}
          onDragEnter={(event) => {
            if (!stop(event)) return
            depth.current += 1
            setOver(true)
          }}
          onDragLeave={(event) => {
            if (!stop(event)) return
            depth.current = Math.max(0, depth.current - 1)
            if (depth.current === 0) setOver(false)
          }}
          onDragOver={(event) => {
            if (stop(event)) event.dataTransfer.dropEffect = "copy"
          }}
          onDrop={(event) => {
            if (!stop(event)) return
            depth.current = 0
            setOver(false)
            take(Array.from(event.dataTransfer.files))
          }}
          type="button"
        >
          <span
            className={cn(
              "flex size-12 items-center justify-center rounded-xl bg-secondary text-secondary-foreground transition-transform duration-150 ease-[var(--ease-out)] motion-reduce:transition-none",
              over && "scale-110"
            )}
          >
            <UploadCloudIcon className="size-6" />
          </span>
          <span className="flex flex-col gap-1">
            <span className="text-sm font-medium">{over ? "Suelta para añadir" : "Arrastra archivos aquí o haz clic para elegirlos"}</span>
            <span className="text-xs text-muted-foreground">Puedes elegir varios a la vez.</span>
          </span>
        </button>
        <ul className="grid gap-2 text-xs text-muted-foreground sm:grid-cols-2">
          <li className="flex items-start gap-2">
            <FileTextIcon aria-hidden className="mt-0.5 size-4 shrink-0" />
            <span>
              <span className="font-medium text-foreground">PDF</span> para documentos: se lee el texto y se divide en fragmentos.
            </span>
          </li>
          <li className="flex items-start gap-2">
            <ImageIcon aria-hidden className="mt-0.5 size-4 shrink-0" />
            <span>
              <span className="font-medium text-foreground">PNG o JPG</span> para facturas: se leen con OCR y se extraen los campos.
            </span>
          </li>
        </ul>
        <p className="text-xs text-muted-foreground">Al elegirlos la ventana se cierra: el avance sigue en una notificación.</p>
      </DialogContent>
    </Dialog>
  )
}
