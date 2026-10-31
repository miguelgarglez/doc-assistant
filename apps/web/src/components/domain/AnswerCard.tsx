"use client"

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { CitationChips } from "@/components/domain/CitationChips"
import { MessageActions } from "@/components/ai/message-actions"
import { useToast } from "@/components/ui/toast"
import { copyText } from "@/lib/clipboard"
import type { Citation } from "@/lib/api/types"
import { CheckIcon, CopyIcon } from "lucide-react"
import { useState } from "react"

type AnswerCardProps = {
  question: string
  answer: string
  citations: readonly Citation[]
  selectedChunkId?: string | null
  onSelectCitation: (citation: Citation) => void
  onRegenerate?: () => void
}

export function AnswerCard({
  question,
  answer,
  citations,
  selectedChunkId = null,
  onSelectCitation,
  onRegenerate,
}: AnswerCardProps) {
  const { toast } = useToast()
  const [copiedCitation, setCopiedCitation] = useState<string | null>(null)

  async function copyCitation(citation: Citation) {
    const ok = await copyText(citation.quote)
    if (ok) {
      setCopiedCitation(citation.chunk_id)
      toast("Cita copiada", "success")
      window.setTimeout(() => setCopiedCitation(null), 1600)
    } else {
      toast("No se pudo copiar")
    }
  }

  return (
    <Card data-testid="answer-card" className="shadow-[var(--shadow-panel)]">
      <CardHeader>
        <CardTitle className="font-heading">Respuesta</CardTitle>
        <CardDescription className="text-sm leading-relaxed">
          {question}
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-5">
        <p className="text-sm leading-relaxed text-foreground sm:text-[0.95rem]">
          {answer}
        </p>
        <div className="flex flex-col gap-2">
          <CitationChips
            citations={citations}
            selectedChunkId={selectedChunkId}
            onSelect={onSelectCitation}
          />
          {citations.length > 0 ? (
            <div className="flex flex-wrap gap-1">
              {citations.map((citation) => (
                <Button
                  key={`copy-${citation.chunk_id}`}
                  type="button"
                  size="xs"
                  variant="ghost"
                  onClick={() => void copyCitation(citation)}
                  aria-label={`Copiar cita de ${citation.doc}`}
                  data-testid={`copy-citation-${citation.chunk_id}`}
                >
                  {copiedCitation === citation.chunk_id ? (
                    <CheckIcon />
                  ) : (
                    <CopyIcon />
                  )}
                  Copiar cita
                </Button>
              ))}
            </div>
          ) : null}
        </div>
        <MessageActions
          answer={answer}
          citations={citations}
          onRegenerate={onRegenerate}
        />
      </CardContent>
    </Card>
  )
}
