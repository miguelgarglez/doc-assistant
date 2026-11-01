"use client"

import { ThumbsDownIcon } from "lucide-react"
import { useState } from "react"
import { toast } from "sonner"

import { MessageAction } from "@/components/ai-elements/message"
import { useConversation } from "@/components/providers/chat-provider"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"

export function FeedbackAction({ requestId }: { requestId: string }) {
  const { conversationId } = useConversation()
  const [open, setOpen] = useState(false)
  const [comment, setComment] = useState("")
  const [includeContext, setIncludeContext] = useState(false)
  const [sending, setSending] = useState(false)

  async function send() {
    setSending(true)
    try {
      const response = await fetch("/api/history/feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ conversation_id: conversationId(), request_id: requestId, comment: comment || null, include_context: includeContext }),
      })
      if (!response.ok) throw new Error("feedback unavailable")
      setOpen(false)
      setComment("")
      setIncludeContext(false)
      toast.success("Respuesta enviada para revisión")
    } catch {
      toast.error("No se pudo enviar la respuesta para revisión")
    } finally {
      setSending(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger render={<MessageAction label="Respuesta incorrecta" />}><ThumbsDownIcon /></DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Respuesta incorrecta</DialogTitle>
          <DialogDescription>Una persona revisará tu aviso antes de usarlo en evaluaciones.</DialogDescription>
        </DialogHeader>
        <div className="flex flex-col gap-4">
          <div className="flex flex-col gap-2">
            <Label htmlFor={`feedback-${requestId}`}>Comentario opcional</Label>
            <Textarea id={`feedback-${requestId}`} maxLength={4000} value={comment} onChange={(event) => setComment(event.target.value)} />
          </div>
          <label className="flex items-start gap-2 text-sm">
            <input type="checkbox" checked={includeContext} onChange={(event) => setIncludeContext(event.target.checked)} />
            <span>Incluir pregunta, respuesta y contexto. Puede contener datos de documentos o facturas.</span>
          </label>
        </div>
        <DialogFooter>
          <Button type="button" onClick={() => void send()} disabled={sending}>Enviar para revisión</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
