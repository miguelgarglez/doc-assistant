"use client"

import { useState } from "react"

import { AnswerCard } from "@/components/domain/AnswerCard"
import { AskErrorNotice } from "@/components/domain/AskErrorNotice"
import { AskLoadingSkeleton } from "@/components/domain/AskLoadingSkeleton"
import { QuestionBox } from "@/components/domain/QuestionBox"
import { RefusalNotice } from "@/components/domain/RefusalNotice"
import { SourceViewer } from "@/components/domain/SourceViewer"
import { useAsk } from "@/hooks/use-ask"
import { citationPage, sourcePageUrl } from "@/lib/api/source-url"
import type { Citation } from "@/lib/api/types"

export function AskWorkspace() {
  const { status, ask } = useAsk()
  const [selectedIndex, setSelectedIndex] = useState(0)

  const loading = status.kind === "loading"
  const citations =
    status.kind === "success" && status.data.ok ? status.data.citations : []
  const safeIndex =
    citations.length === 0 ? 0 : Math.min(selectedIndex, citations.length - 1)
  const selected: Citation | null =
    citations.length > 0 ? (citations[safeIndex] ?? null) : null
  const page = selected ? (citationPage(selected) ?? null) : null
  const pageImageSrc =
    selected && page !== null ? sourcePageUrl(selected.doc, page) : null

  function handleSelectCitation(citation: Citation) {
    const index = citations.findIndex((item) => item.chunk_id === citation.chunk_id)
    if (index >= 0) {
      setSelectedIndex(index)
    }
  }

  function handleAsk(question: string) {
    setSelectedIndex(0)
    void ask(question)
  }

  function handleRetry() {
    if (status.kind === "error") {
      setSelectedIndex(0)
      void ask(status.question)
    }
  }

  return (
    <div className="flex flex-col gap-8">
      <section aria-labelledby="ask-heading" className="flex flex-col gap-4">
        <div className="flex flex-col gap-1">
          <h2 id="ask-heading" className="text-lg font-medium text-foreground">
            Consulta
          </h2>
          <p className="text-sm leading-relaxed text-muted-foreground">
            Pregunta sobre la documentación técnica indexada. Las respuestas
            incluyen citas verificables con página y fragmento.
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

      {loading ? <AskLoadingSkeleton /> : null}

      {status.kind === "error" ? (
        <AskErrorNotice error={status.error} onRetry={handleRetry} />
      ) : null}

      {status.kind === "success" && !status.data.ok ? (
        <RefusalNotice reason={status.data.reason} />
      ) : null}

      {status.kind === "success" && status.data.ok ? (
        <section
          className="grid grid-cols-1 gap-6 lg:grid-cols-2"
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
            citationIndex={safeIndex}
            citationCount={citations.length}
            onPrevCitation={() =>
              setSelectedIndex((index) => Math.max(0, index - 1))
            }
            onNextCitation={() =>
              setSelectedIndex((index) =>
                Math.min(citations.length - 1, index + 1)
              )
            }
          />
        </section>
      ) : null}
    </div>
  )
}
