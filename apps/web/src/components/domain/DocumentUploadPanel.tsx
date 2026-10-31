"use client"

import { UploadDropzone } from "@/components/domain/UploadDropzone"
import {
  useDocumentUpload,
  type DocumentUploadStatus,
} from "@/hooks/use-document-upload"

type DocumentUploadApi = {
  status: DocumentUploadStatus
  upload: (file: File) => Promise<void>
  retry: () => void
}

type DocumentUploadPanelProps = {
  api?: DocumentUploadApi
}

export function DocumentUploadPanel({ api }: DocumentUploadPanelProps) {
  const internal = useDocumentUpload()
  const { status, upload, retry } = api ?? internal
  const uploading = status.kind === "uploading"
  const error = status.kind === "error" ? status.error : null
  const progress = status.kind === "uploading" ? status.progress : null

  return (
    <section
      aria-labelledby="document-upload-heading"
      className="flex flex-col gap-3"
      data-testid="document-upload-panel"
    >
      <UploadDropzone
        accept="application/pdf,.pdf"
        acceptLabel="PDF técnico"
        title="Indexar PDF"
        description="Manual o ficha técnica. Si ya estaba indexado, se indica sin duplicar."
        compact
        uploading={uploading}
        progress={progress}
        error={error}
        onFile={(file) => void upload(file)}
        onRetry={retry}
        data-testid="document-upload"
      />
      {status.kind === "success" ? (
        <p
          className="text-sm text-muted-foreground"
          role="status"
          data-testid="document-upload-result"
        >
          {status.data.created
            ? `Indexado: ${status.data.n_chunks} fragmentos (${status.data.doc_id}).`
            : `Ya indexado: ${status.data.doc_id} (${status.data.n_chunks} fragmentos).`}
        </p>
      ) : null}
    </section>
  )
}
