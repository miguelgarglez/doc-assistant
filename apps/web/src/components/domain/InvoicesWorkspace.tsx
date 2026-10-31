"use client"

import { InvoiceList } from "@/components/domain/InvoiceList"
import { InvoiceReviewCard } from "@/components/domain/InvoiceReviewCard"
import { UploadDropzone } from "@/components/domain/UploadDropzone"
import { AskErrorNotice } from "@/components/domain/AskErrorNotice"
import { useInvoices } from "@/hooks/use-invoices"

export function InvoicesWorkspace({ api }: { api: ReturnType<typeof useInvoices> }) {
  const {
    invoices,
    listLoading,
    listError,
    uploadStatus,
    selected,
    upload,
    retryUpload,
    selectFromList,
    refresh,
    cancelUpload,
  } = api

  const uploading = uploadStatus.kind === "uploading"
  const uploadError =
    uploadStatus.kind === "error" ? uploadStatus.error : null
  const progress =
    uploadStatus.kind === "uploading" ? uploadStatus.progress : null

  return (
    <div className="flex flex-col gap-8" data-testid="invoices-workspace">
      <UploadDropzone
        accept="image/png,image/jpeg,.png,.jpg,.jpeg"
        acceptLabel="PNG o JPG"
        title="Subir factura"
        description="Arrastra o elige una imagen de factura. La extracción muestra el estado ok o revisar sin inventar campos."
        uploading={uploading}
        progress={progress}
        error={uploadError}
        onFile={(file) => void upload(file)}
        onRetry={retryUpload}
        onCancel={cancelUpload}
        data-testid="invoice-upload"
      />

      <section
        aria-labelledby="invoice-list-heading"
        className="flex flex-col gap-3"
      >
        <div className="flex flex-col gap-1">
          <h2
            id="invoice-list-heading"
            className="text-lg font-medium text-foreground"
          >
            Indexadas
          </h2>
          <p className="text-sm text-muted-foreground">
            Pulsa una factura para abrir su ficha.
          </p>
        </div>
        {listError ? (
          <AskErrorNotice error={listError} onRetry={() => void refresh()} />
        ) : (
          <InvoiceList
            invoices={invoices}
            selectedNumero={selected?.record.numero ?? null}
            onSelect={selectFromList}
            loading={listLoading}
          />
        )}
      </section>

      {selected ? <InvoiceReviewCard data={selected} /> : null}
    </div>
  )
}
