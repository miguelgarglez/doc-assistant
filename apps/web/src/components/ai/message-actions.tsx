"use client"

import {
  CheckIcon,
  CopyIcon,
  FileTextIcon,
  RefreshCwIcon,
} from "lucide-react"
import { useState } from "react"

import { Button } from "@/components/ui/button"
import { useToast } from "@/components/ui/toast"
import { copyText, formatAnswerMarkdown } from "@/lib/clipboard"
import type { Citation } from "@/lib/api/types"
import { cn } from "@/lib/utils"

type MessageActionsProps = {
  answer: string
  citations: readonly Citation[]
  onRegenerate?: () => void
  className?: string
}

export function MessageActions({
  answer,
  citations,
  onRegenerate,
  className,
}: MessageActionsProps) {
  const { toast } = useToast()
  const [copied, setCopied] = useState<"answer" | "markdown" | null>(null)

  async function handleCopyAnswer() {
    const ok = await copyText(answer)
    if (ok) {
      setCopied("answer")
      toast("Respuesta copiada", "success")
      window.setTimeout(() => setCopied(null), 1600)
    } else {
      toast("No se pudo copiar")
    }
  }

  async function handleCopyMarkdown() {
    const ok = await copyText(formatAnswerMarkdown(answer, citations))
    if (ok) {
      setCopied("markdown")
      toast("Markdown con citas copiado", "success")
      window.setTimeout(() => setCopied(null), 1600)
    } else {
      toast("No se pudo copiar")
    }
  }

  return (
    <div
      className={cn("flex flex-wrap items-center gap-1", className)}
      role="group"
      aria-label="Acciones de la respuesta"
      data-testid="message-actions"
    >
      <Button
        type="button"
        size="sm"
        variant="ghost"
        onClick={() => void handleCopyAnswer()}
        aria-label="Copiar respuesta"
        data-testid="copy-answer"
      >
        {copied === "answer" ? <CheckIcon /> : <CopyIcon />}
        Copiar
      </Button>
      <Button
        type="button"
        size="sm"
        variant="ghost"
        onClick={() => void handleCopyMarkdown()}
        aria-label="Copiar como Markdown con citas"
        data-testid="copy-markdown"
      >
        {copied === "markdown" ? <CheckIcon /> : <FileTextIcon />}
        Markdown
      </Button>
      {onRegenerate ? (
        <Button
          type="button"
          size="sm"
          variant="ghost"
          onClick={onRegenerate}
          aria-label="Regenerar respuesta"
          data-testid="regenerate"
        >
          <RefreshCwIcon />
          Regenerar
        </Button>
      ) : null}
    </div>
  )
}
