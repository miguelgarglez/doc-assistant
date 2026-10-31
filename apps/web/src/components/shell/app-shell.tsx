"use client"

import { UploadCloudIcon } from "lucide-react"
import { usePathname, useRouter } from "next/navigation"
import { useEffect, useRef, useState, type ReactNode } from "react"

import { usePromptInput } from "@/components/ai-elements/prompt-input"
import { useAddSources } from "@/components/providers/add-sources-provider"
import { useUploads, type UploadOrigin } from "@/components/providers/uploads-provider"
import { AppSidebar, NAV_ITEMS } from "@/components/shell/app-sidebar"
import { ShortcutsHelp } from "@/components/shell/shortcuts-help"
import { SidebarInset, SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar"
import { isEditableTarget, isModKey } from "@/lib/shortcuts"
import { cn } from "@/lib/utils"

/**
 * Full-height shell: the sidebar is fixed, the page decides what scrolls.
 * It also owns the window-level concerns: file drop, global shortcuts and the help dialog.
 */
export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname()
  const router = useRouter()
  const { enqueue } = useUploads()
  const addSources = useAddSources()
  const { textareaRef } = usePromptInput()
  const [helpOpen, setHelpOpen] = useState(false)
  const [dragging, setDragging] = useState(false)
  const depth = useRef(0)
  const origin: UploadOrigin = pathname === "/" ? "chat" : "sources"
  const title = NAV_ITEMS.find((item) => (item.href === "/" ? pathname === "/" : pathname.startsWith(item.href)))?.label ?? "Doc Assistant"

  useEffect(() => {
    // While the dialog is open its own drop zone takes the files.
    if (addSources.open) return
    const hasFiles = (event: DragEvent) => Array.from(event.dataTransfer?.types ?? []).includes("Files")
    const enter = (event: DragEvent) => {
      if (!hasFiles(event)) return
      event.preventDefault()
      depth.current += 1
      setDragging(true)
    }
    const over = (event: DragEvent) => {
      if (hasFiles(event)) event.preventDefault()
    }
    const leave = (event: DragEvent) => {
      if (!hasFiles(event)) return
      depth.current = Math.max(0, depth.current - 1)
      if (depth.current === 0) setDragging(false)
    }
    const drop = (event: DragEvent) => {
      if (!hasFiles(event)) return
      event.preventDefault()
      depth.current = 0
      setDragging(false)
      const files = Array.from(event.dataTransfer?.files ?? [])
      if (files.length > 0) enqueue(files, origin)
    }
    window.addEventListener("dragenter", enter)
    window.addEventListener("dragover", over)
    window.addEventListener("dragleave", leave)
    window.addEventListener("drop", drop)
    return () => {
      window.removeEventListener("dragenter", enter)
      window.removeEventListener("dragover", over)
      window.removeEventListener("dragleave", leave)
      window.removeEventListener("drop", drop)
    }
  }, [enqueue, origin, addSources.open])

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.isComposing || event.keyCode === 229 || helpOpen) return
      if (isModKey(event) && event.key.toLowerCase() === "k") {
        event.preventDefault()
        if (pathname === "/") textareaRef.current?.focus()
        else router.push("/")
        return
      }
      const help = (event.key === "?" && !isEditableTarget(event.target)) || (isModKey(event) && event.key === "/")
      if (help) {
        event.preventDefault()
        setHelpOpen(true)
      }
    }
    window.addEventListener("keydown", onKeyDown)
    return () => window.removeEventListener("keydown", onKeyDown)
  }, [helpOpen, pathname, router, textareaRef])

  return (
    <SidebarProvider className="h-dvh min-h-0 overflow-hidden">
      <AppSidebar />
      <SidebarInset className="h-dvh min-h-0 min-w-0 overflow-hidden">
        <header className="flex h-12 shrink-0 items-center gap-2 border-b border-border bg-background px-3 md:hidden">
          <SidebarTrigger aria-label="Abrir el menú" />
          <span className="font-heading text-sm font-semibold">{title}</span>
        </header>
        <div className="flex min-h-0 flex-1 flex-col">{children}</div>
      </SidebarInset>
      <ShortcutsHelp open={helpOpen} onClose={() => setHelpOpen(false)} />
      <div
        aria-hidden={!dragging}
        className={cn(
          "pointer-events-none fixed inset-0 z-50 flex items-center justify-center bg-background/80 p-6 opacity-0 backdrop-blur-sm transition-opacity duration-150 ease-[var(--ease-out)]",
          dragging && "opacity-100"
        )}
        data-testid="drop-overlay"
      >
        <div className="flex max-w-sm flex-col items-center gap-3 rounded-2xl border-2 border-dashed border-primary bg-card px-10 py-12 text-center">
          <UploadCloudIcon className="size-8 text-primary" />
          <p className="font-medium">Suelta para añadir como fuente</p>
          <p className="text-sm text-muted-foreground">PDF para documentos, PNG o JPG para facturas.</p>
        </div>
      </div>
    </SidebarProvider>
  )
}
