"use client"

import { AskWorkspace } from "@/components/domain/AskWorkspace"
import { useInvoices } from "@/hooks/use-invoices"

export default function HomePage() {
  const invoices = useInvoices()
  return <main className="mx-auto w-full max-w-6xl px-4 py-6 sm:px-6"><AskWorkspace onInvoice={async (file) => { await invoices.upload(file) }} />{invoices.uploadStatus.kind === "uploading" ? <p role="status" className="mt-4 text-sm">Subiendo {invoices.uploadStatus.fileName}: {invoices.uploadStatus.progress}%</p> : invoices.uploadStatus.kind === "error" ? <p role="alert" className="mt-4 text-sm">{invoices.uploadStatus.error.message}</p> : invoices.uploadStatus.kind === "success" ? <p role="status" className="mt-4 text-sm">Fuente añadida.</p> : null}</main>
}
