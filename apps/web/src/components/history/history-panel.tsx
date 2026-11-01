"use client"

import { HistoryIcon, Trash2Icon } from "lucide-react"
import { useRouter } from "next/navigation"
import { useCallback, useEffect, useState } from "react"
import { toast } from "sonner"

import { useConversation } from "@/components/providers/chat-provider"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Empty, EmptyDescription } from "@/components/ui/empty"
import { Input } from "@/components/ui/input"
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet"
import { SidebarMenuButton } from "@/components/ui/sidebar"

type Conversation = { conversation_id: string; question: string; updated_at: string; count: number }
const PAGE_SIZE = 50

export function HistoryPanel() {
  const router = useRouter()
  const { openConversation, clear, conversationId, busy } = useConversation()
  const [open, setOpen] = useState(false)
  const [confirm, setConfirm] = useState(false)
  const [search, setSearch] = useState("")
  const [items, setItems] = useState<Conversation[]>([])
  const [offset, setOffset] = useState(0)
  const [hasMore, setHasMore] = useState(false)
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)

  const load = useCallback(async (nextOffset: number, append = false, signal?: AbortSignal) => {
    setLoading(true)
    setError("")
    try {
      const query = new URLSearchParams({ limit: String(PAGE_SIZE), offset: String(nextOffset), search })
      const response = await fetch(`/api/history/conversations?${query}`, { signal })
      if (!response.ok) throw new Error()
      const page: Conversation[] = await response.json()
      setItems((current) => append ? [...current, ...page] : page)
      setOffset(nextOffset + page.length)
      setHasMore(page.length === PAGE_SIZE)
    } catch {
      if (!signal?.aborted) setError("No se pudo cargar el historial.")
    } finally {
      if (!signal?.aborted) setLoading(false)
    }
  }, [search])

  useEffect(() => {
    if (!open) return
    const controller = new AbortController()
    const timer = window.setTimeout(() => void load(0, false, controller.signal), 150)
    return () => {
      window.clearTimeout(timer)
      controller.abort()
    }
  }, [open, load])

  useEffect(() => {
    const key = (event: KeyboardEvent) => {
      if (event.altKey && event.code === "KeyH" && !event.ctrlKey && !event.metaKey && !event.shiftKey) {
        event.preventDefault()
        setOpen(true)
      }
    }
    window.addEventListener("keydown", key)
    return () => window.removeEventListener("keydown", key)
  }, [])

  async function show(id: string) {
    try {
      await openConversation(id)
      setOpen(false)
      router.push("/")
    } catch {
      toast.error("No se pudo abrir la conversación")
    }
  }

  async function remove(id?: string) {
    try {
      const response = await fetch(`/api/history/conversations${id ? `/${encodeURIComponent(id)}` : ""}`, { method: "DELETE" })
      if (!response.ok) throw new Error()
      if (!id || id === conversationId()) clear()
      setConfirm(false)
      await load(0)
    } catch {
      toast.error("No se pudo borrar el historial")
    }
  }

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger render={<SidebarMenuButton />}><HistoryIcon /><span>Historial</span></SheetTrigger>
      <SheetContent className="data-[side=right]:w-full data-[side=right]:sm:max-w-none">
        <SheetHeader>
          <SheetTitle>Historial</SheetTitle>
          <SheetDescription>Conversaciones guardadas en este equipo.</SheetDescription>
        </SheetHeader>
        <div className="mx-auto flex min-h-0 w-full max-w-3xl flex-1 flex-col gap-4 px-4 pb-4">
          <div className="flex gap-2">
            <Input aria-label="Buscar en el historial" placeholder="Buscar conversaciones" value={search} onChange={(event) => setSearch(event.target.value)} />
            <Button onClick={() => setConfirm(true)} variant="outline">Borrar todo</Button>
          </div>
          {error ? <p role="alert">{error}</p> : null}
          {!loading && items.length === 0 && !error ? <Empty><EmptyDescription>No hay conversaciones guardadas.</EmptyDescription></Empty> : null}
          <div className="min-h-0 flex-1 overflow-y-auto">
            <ul className="flex flex-col gap-2">
              {items.map((item) => (
                <li className="flex items-center gap-2 border-b py-2" key={item.conversation_id}>
                  <button className="min-w-0 flex-1 cursor-pointer text-left" disabled={busy} onClick={() => void show(item.conversation_id)} type="button">
                    <span className="block truncate font-medium">{item.question.trim() || "Conversación"}</span>
                    <span className="text-xs text-muted-foreground">{new Date(item.updated_at).toLocaleString("es-ES")} · {item.count} consultas</span>
                  </button>
                  <Button aria-label={`Borrar ${item.question.trim() || "conversación"}`} onClick={() => void remove(item.conversation_id)} size="icon-sm" variant="ghost"><Trash2Icon data-icon="inline-start" /></Button>
                </li>
              ))}
            </ul>
            {hasMore ? <Button disabled={loading} onClick={() => void load(offset, true)} variant="ghost">Cargar más</Button> : null}
          </div>
        </div>
      </SheetContent>
      <Dialog open={confirm} onOpenChange={setConfirm}>
        <DialogContent>
          <DialogHeader><DialogTitle>¿Borrar todo el historial?</DialogTitle><DialogDescription>Se borrarán las conversaciones y sus avisos de feedback de este equipo.</DialogDescription></DialogHeader>
          <DialogFooter><Button onClick={() => setConfirm(false)} variant="outline">Cancelar</Button><Button onClick={() => void remove()} variant="destructive">Borrar todo</Button></DialogFooter>
        </DialogContent>
      </Dialog>
    </Sheet>
  )
}
