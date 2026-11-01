"use client"

import type { ReactNode } from "react"

import { UploadsProvider } from "@/features/uploads"
import { useSources } from "@/features/sources"

export function UploadsWithSources({ children }: { children: ReactNode }) {
  const { refresh } = useSources()
  return <UploadsProvider onUploaded={refresh}>{children}</UploadsProvider>
}
