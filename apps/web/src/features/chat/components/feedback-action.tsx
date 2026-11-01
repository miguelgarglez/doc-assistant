"use client"

import { ThumbsDownIcon } from "lucide-react"
import { useState } from "react"
import { toast } from "sonner"

import { MessageAction } from "@/components/ai-elements/message"
import { useConversation } from "@/features/chat/chat-provider"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field"
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
        <FieldGroup>
          <Field>
            <FieldLabel htmlFor={`feedback-${requestId}`}>Comentario opcional</FieldLabel>
            <Textarea id={`feedback-${requestId}`} maxLength={4000} value={comment} onChange={(event) => setComment(event.target.value)} />
          </Field>
          <Field orientation="horizontal">
            <Checkbox id={`feedback-context-${requestId}`} checked={includeContext} onCheckedChange={setIncludeContext} />
            <FieldLabel htmlFor={`feedback-context-${requestId}`}>Incluir pregunta, respuesta y contexto. Puede contener datos de documentos o facturas.</FieldLabel>
          </Field>
        </FieldGroup>
        <DialogFooter>
          <Button type="button" onClick={() => void send()} disabled={sending}>Enviar para revisión</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
