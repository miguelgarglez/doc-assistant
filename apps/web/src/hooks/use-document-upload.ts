"use client"

import { useState } from "react"

import type { DocumentUploadResponse, ErrorBody } from "@/lib/api/types"
import { uploadDocumentFile } from "@/lib/api/upload"

export type DocumentUploadStatus =
  | { kind: "idle" }
  | { kind: "uploading"; fileName: string }
  | { kind: "success"; data: DocumentUploadResponse }
  | { kind: "error"; file: File; error: ErrorBody }

export function useDocumentUpload() {
  const [status, setStatus] = useState<DocumentUploadStatus>({ kind: "idle" })

  async function upload(file: File) {
    setStatus({ kind: "uploading", fileName: file.name })
    const result = await uploadDocumentFile(file)
    if (!result.ok) {
      setStatus({ kind: "error", file, error: result.error })
      return
    }
    setStatus({ kind: "success", data: result.data })
  }

  function retry() {
    if (status.kind === "error") {
      void upload(status.file)
    }
  }

  function reset() {
    setStatus({ kind: "idle" })
  }

  return { status, upload, retry, reset }
}
