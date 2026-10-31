"use client"

import { useRef, useState } from "react"

import type { DocumentUploadResponse, ErrorBody } from "@/lib/api/types"
import { uploadDocumentFile } from "@/lib/api/upload"

export type DocumentUploadStatus =
  | { kind: "idle" }
  | { kind: "uploading"; fileName: string; progress: number }
  | { kind: "success"; data: DocumentUploadResponse }
  | { kind: "error"; file: File; error: ErrorBody }

export function useDocumentUpload() {
  const [status, setStatus] = useState<DocumentUploadStatus>({ kind: "idle" })

  const queue = useRef<Promise<void>>(Promise.resolve())
  const abortRef = useRef<AbortController | null>(null)

  async function run(file: File) {
    const controller = new AbortController()
    abortRef.current = controller
    setStatus({ kind: "uploading", fileName: file.name, progress: 0 })
    const result = await uploadDocumentFile(file, (progress) => {
      setStatus({ kind: "uploading", fileName: file.name, progress })
    }, controller.signal)
    abortRef.current = null
    if (!result.ok) {
      setStatus({ kind: "error", file, error: result.error })
      return
    }
    setStatus({ kind: "success", data: result.data })
  }

  function upload(file: File) {
    const next = queue.current.then(() => run(file))
    queue.current = next
    return next
  }

  function cancel() {
    abortRef.current?.abort()
  }

  function retry() {
    if (status.kind === "error") {
      void upload(status.file)
    }
  }

  function reset() {
    setStatus({ kind: "idle" })
  }

  return { status, upload, retry, reset, cancel }
}
