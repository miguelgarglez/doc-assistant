"use client"

import { UploadDropzone } from "@/components/domain/UploadDropzone"
import { useDocumentUpload } from "@/hooks/use-document-upload"

export function DocumentUploadPanel() {
  const { status, upload, retry } = useDocumentUpload()
  const uploading = status.kind === "uploading"
  const error = status.kind === "error" ? status.error : null

  return (
    <section
      aria-labelledby="document-upload-heading"
      className="flex flex-col gap-3"
      data-testid="document-upload-panel"
    >
      <UploadDropzone
        accept="application/pdf,.pdf"
        acceptLabel="PDF técnico"
        title="Indexar PDF (opcional)"
        description="Sube un manual o ficha técnica. Si el contenido ya estaba indexado, se indica sin duplicar."
        compact
        uploading={uploading}
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
