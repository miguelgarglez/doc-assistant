"use client"

import { useCallback, useEffect, useRef, useState } from "react"

import { api } from "@/lib/api/client"
import { toErrorBody } from "@/lib/api/errors"
import type { ErrorBody, Invoice, InvoiceUploadResponse } from "@/lib/api/types"
import { uploadInvoiceFile } from "@/lib/api/upload"

export type InvoiceUploadStatus =
  | { kind: "idle" }
  | { kind: "uploading"; fileName: string; progress: number }
  | { kind: "success"; data: InvoiceUploadResponse }
  | { kind: "error"; file: File; error: ErrorBody }

export function useInvoices() {
  const abortRef = useRef<AbortController | null>(null)
  const [invoices, setInvoices] = useState<Invoice[]>([])
  const [listLoading, setListLoading] = useState(true)
  const [listError, setListError] = useState<ErrorBody | null>(null)
  const [uploadStatus, setUploadStatus] = useState<InvoiceUploadStatus>({
    kind: "idle",
  })
  const [selected, setSelected] = useState<InvoiceUploadResponse | null>(null)
  const [reviewsByNumero, setReviewsByNumero] = useState<
    Record<string, InvoiceUploadResponse>
  >({})

  const applyList = useCallback((data: Invoice[] | undefined, error: unknown) => {
    if (error) {
      setListError(toErrorBody(error))
      setListLoading(false)
      return
    }
    setListError(null)
    setInvoices(data ?? [])
    setListLoading(false)
  }, [])

  useEffect(() => {
    let cancelled = false
    void api.GET("/invoices").then(({ data, error }) => {
      if (cancelled) {
        return
      }
      applyList(data, error)
    })
    return () => {
      cancelled = true
    }
  }, [applyList])

  async function refresh() {
    setListLoading(true)
    const { data, error } = await api.GET("/invoices")
    applyList(data, error)
  }

  async function upload(file: File) {
    const controller = new AbortController()
    abortRef.current = controller
    setUploadStatus({ kind: "uploading", fileName: file.name, progress: 0 })
    const result = await uploadInvoiceFile(file, (progress) => {
      setUploadStatus({ kind: "uploading", fileName: file.name, progress })
    }, controller.signal)
    abortRef.current = null
    if (!result.ok) {
      setUploadStatus({ kind: "error", file, error: result.error })
      return false
    }
    setUploadStatus({ kind: "success", data: result.data })
    setSelected(result.data)
    setReviewsByNumero((current) => ({
      ...current,
      [result.data.record.numero]: result.data,
    }))
    await refresh()
    return true
  }

  function retryUpload() {
    if (uploadStatus.kind === "error") {
      void upload(uploadStatus.file)
    }
  }

  function selectFromList(invoice: Invoice) {
    const cached = reviewsByNumero[invoice.numero]
    if (cached) {
      setSelected(cached)
      return
    }
    setSelected({
      record: invoice,
      estado: "",
      motivo: null,
      evidencias: {},
      flags: {},
      fichero: null,
    })
  }

  return {
    invoices,
    listLoading,
    listError,
    uploadStatus,
    selected,
    upload,
    retryUpload,
    selectFromList,
    refresh,
    cancelUpload: () => abortRef.current?.abort(),
  }
}
