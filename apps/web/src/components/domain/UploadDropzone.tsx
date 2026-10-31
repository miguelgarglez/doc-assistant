"use client"

import { useState } from "react"
import { UploadIcon } from "lucide-react"

import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import type { UploadFile } from "@/lib/domain/types"

type UploadDropzoneProps = {
  files: readonly UploadFile[]
}

function formatBytes(sizeBytes: number) {
  if (sizeBytes < 1024) {
    return `${sizeBytes} B`
  }
  if (sizeBytes < 1024 * 1024) {
    return `${(sizeBytes / 1024).toFixed(1)} KB`
  }
  return `${(sizeBytes / (1024 * 1024)).toFixed(1)} MB`
}

export function UploadDropzone({ files }: UploadDropzoneProps) {
  const [active, setActive] = useState(false)

  return (
    <Card>
      <CardHeader>
        <CardTitle>Documentos</CardTitle>
        <CardDescription>
          Arrastra facturas o extractos para la revisión (UI de ejemplo).
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <div
          className={
            active
              ? "flex flex-col items-center gap-3 rounded-lg border border-primary bg-muted/60 px-6 py-10 text-center"
              : "flex flex-col items-center gap-3 rounded-lg border border-dashed border-border px-6 py-10 text-center"
          }
          onDragEnter={(event) => {
            event.preventDefault()
            setActive(true)
          }}
          onDragOver={(event) => {
            event.preventDefault()
            setActive(true)
          }}
          onDragLeave={(event) => {
            event.preventDefault()
            setActive(false)
          }}
          onDrop={(event) => {
            event.preventDefault()
            setActive(false)
          }}
        >
          <UploadIcon className="size-5 text-muted-foreground" />
          <p className="text-sm text-muted-foreground">
            Suelta archivos aquí o elige desde el disco.
          </p>
          <Button type="button" variant="outline" size="sm">
            Elegir archivos
          </Button>
        </div>
        <ul className="flex flex-col gap-2">
          {files.map((file) => (
            <li
              key={file.name}
              className="flex items-center justify-between gap-3 text-sm"
            >
              <span className="truncate text-foreground">{file.name}</span>
              <span className="shrink-0 text-muted-foreground">
                {formatBytes(file.sizeBytes)} · {file.mimeType}
              </span>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  )
}
