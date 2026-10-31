"use client"

import { useState } from "react"

import { AnswerCard } from "@/components/domain/AnswerCard"
import { AskErrorNotice } from "@/components/domain/AskErrorNotice"
import { QuestionBox } from "@/components/domain/QuestionBox"
import { RefusalNotice } from "@/components/domain/RefusalNotice"
import { SourceViewer } from "@/components/domain/SourceViewer"
import { useAsk } from "@/hooks/use-ask"
import { citationPage, sourcePageUrl } from "@/lib/api/source-url"
import type { Citation } from "@/lib/api/types"

export function AskWorkspace() {
  const { status, ask } = useAsk()
  const [selected, setSelected] = useState<Citation | null>(null)

  const loading = status.kind === "loading"
  const page = selected ? (citationPage(selected) ?? null) : null
  const pageImageSrc =
    selected && page !== null ? sourcePageUrl(selected.doc, page) : null

  function handleSelectCitation(citation: Citation) {
    setSelected(citation)
  }

  function handleAsk(question: string) {
    setSelected(null)
    void ask(question)
  }

  return (
    <div className="flex flex-col gap-8">
      <section aria-labelledby="ask-heading" className="flex flex-col gap-4">
        <div className="flex flex-col gap-1">
          <h2 id="ask-heading" className="text-lg font-medium text-foreground">
            Consulta
          </h2>
          <p className="text-sm text-muted-foreground">
            Pregunta sobre la normativa indexada. Las respuestas incluyen citas
            verificables.
          </p>
        </div>
        <QuestionBox disabled={loading} onSubmit={handleAsk} />
      </section>

      {status.kind === "idle" ? (
        <p
          className="text-sm text-muted-foreground"
          data-testid="ask-empty"
          role="status"
        >
          Aún no hay consulta. Escribe una pregunta para empezar.
        </p>
      ) : null}

      {loading ? (
        <p className="text-sm text-muted-foreground" role="status" aria-live="polite">
          Consultando…
        </p>
      ) : null}

      {status.kind === "error" ? <AskErrorNotice error={status.error} /> : null}

      {status.kind === "success" && !status.data.ok ? (
        <RefusalNotice reason={status.data.reason} />
      ) : null}

      {status.kind === "success" && status.data.ok ? (
        <section
          className="grid gap-6 lg:grid-cols-2"
          aria-live="polite"
          aria-label="Resultado de la consulta"
        >
          <AnswerCard
            question={status.question}
            answer={status.data.answer}
            citations={status.data.citations}
            selectedChunkId={selected?.chunk_id ?? null}
            onSelectCitation={handleSelectCitation}
          />
          <SourceViewer
            citation={selected}
            pageImageSrc={pageImageSrc}
            page={page}
          />
        </section>
      ) : null}
    </div>
  )
}
