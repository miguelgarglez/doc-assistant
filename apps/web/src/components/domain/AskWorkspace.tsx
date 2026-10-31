"use client"

import { useEffect, useLayoutEffect, useRef, useState } from "react"
import { KeyboardIcon } from "lucide-react"

import {
  Conversation,
  ConversationContent,
  ConversationEmptyState,
  ConversationScrollButton,
} from "@/components/ai/conversation"
import { Suggestion, Suggestions } from "@/components/ai/suggestion"
import { AnswerCard } from "@/components/domain/AnswerCard"
import { AskErrorNotice } from "@/components/domain/AskErrorNotice"
import { AskLoadingSkeleton } from "@/components/domain/AskLoadingSkeleton"
import { DocumentUploadPanel } from "@/components/domain/DocumentUploadPanel"
import {
  QuestionBox,
  type QuestionBoxHandle,
} from "@/components/domain/QuestionBox"
import { RefusalNotice } from "@/components/domain/RefusalNotice"
import { ShortcutsHelp } from "@/components/domain/ShortcutsHelp"
import { SourceViewer } from "@/components/domain/SourceViewer"
import { Button } from "@/components/ui/button"
import { useToast } from "@/components/ui/toast"
import { useAsk } from "@/hooks/use-ask"
import { useDocumentUpload } from "@/hooks/use-document-upload"
import { useQuestionHistory } from "@/hooks/use-question-history"
import { citationPage, sourcePageUrl } from "@/lib/api/source-url"
import {
  classifyDroppedFile,
} from "@/lib/api/upload"
import type { Citation } from "@/lib/api/types"
import { isEditableTarget, isModKey } from "@/lib/shortcuts"

const SUGGESTIONS = [
  "¿Cuál es la carga útil máxima del GR-50?",
  "¿Qué perímetro libre exige la zona de seguridad?",
  "¿Qué interfaz de brida usa el end-effector?",
] as const

export function AskWorkspace({ onInvoice }: { onInvoice: (file: File) => Promise<void> }) {
  const { status, ask, cancel } = useAsk()
  const questionHistory = useQuestionHistory()
  const documentUpload = useDocumentUpload()
  const { toast } = useToast()
  const questionRef = useRef<QuestionBoxHandle>(null)
  const [selectedIndex, setSelectedIndex] = useState(0)
  const [shortcutsOpen, setShortcutsOpen] = useState(false)
  const [viewerOpen, setViewerOpen] = useState(true)

  const loading = status.kind === "loading"
  const citations =
    status.kind === "success" && status.data.ok ? status.data.citations : []
  const safeIndex =
    citations.length === 0 ? 0 : Math.min(selectedIndex, citations.length - 1)
  const selected: Citation | null =
    citations.length > 0 ? (citations[safeIndex] ?? null) : null
  const [pageSel, setPageSel] = useState<{ chunkId: string; index: number } | null>(
    null
  )
  const pageIndex =
    selected && pageSel?.chunkId === selected.chunk_id ? pageSel.index : 0
  const pageCount = selected?.pages.length ?? 0
  const page = selected ? (citationPage(selected, pageIndex) ?? null) : null
  const pageImageSrc =
    selected && page !== null ? sourcePageUrl(selected.doc_id, page) : null

  function handleSelectCitation(citation: Citation) {
    const index = citations.findIndex((item) => item.chunk_id === citation.chunk_id)
    if (index >= 0) {
      setSelectedIndex(index)
      setViewerOpen(true)
    }
  }

  function handleAsk(question: string) {
    setSelectedIndex(0)
    setViewerOpen(true)
    questionHistory.push(question)
    void ask(question)
  }

  function handleRetry() {
    if (status.kind === "error" || status.kind === "cancelled") {
      setSelectedIndex(0)
      void ask(status.question)
    }
  }

  function handleRegenerate() {
    if (status.kind === "success") {
      void ask(status.question)
    }
  }

  function handleFiles(files: File[]) {
    for (const file of files) {
      const kind = classifyDroppedFile(file)
      if (kind === "document") {
        toast(`Subiendo ${file.name}…`)
        void documentUpload.upload(file)
      } else if (kind === "invoice") {
        toast(`Subiendo factura ${file.name}…`)
        void onInvoice(file)
      } else {
        toast(`Tipo no soportado: ${file.name}`)
      }
    }
  }

  // Cache Components (Activity): al ocultar la ruta se limpia el diálogo
  // para que no reaparezca abierto al volver atrás/adelante.
  useLayoutEffect(() => {
    return () => setShortcutsOpen(false)
  }, [])

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (event.isComposing || event.keyCode === 229 || shortcutsOpen) return
      if (isModKey(event) && event.key.toLowerCase() === "k") {
        event.preventDefault()
        questionRef.current?.focus()
        return
      }
      if (
        (isModKey(event) && event.key === "/") ||
        (event.key === "?" && !isEditableTarget(event.target))
      ) {
        event.preventDefault()
        setShortcutsOpen(true)
        return
      }
      if (event.key === "Escape") {
        if (shortcutsOpen) {
          setShortcutsOpen(false)
          return
        }
        if (loading) {
          cancel()
          return
        }
        if (viewerOpen && selected) {
          setViewerOpen(false)
        }
      }
    }
    window.addEventListener("keydown", onKeyDown)
    return () => window.removeEventListener("keydown", onKeyDown)
  }, [cancel, loading, selected, shortcutsOpen, viewerOpen])

  const showEmpty = status.kind === "idle"

  return (
    <div className="flex flex-col gap-8">
      <section aria-labelledby="ask-heading" className="flex flex-col gap-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="flex flex-col gap-1">
            <h2
              id="ask-heading"
              className="font-heading text-lg font-medium text-foreground"
            >
              Consulta
            </h2>
            <p className="max-w-2xl text-sm leading-relaxed text-muted-foreground">
              Pregunta sobre la documentación técnica indexada. Las respuestas
              incluyen citas verificables.
            </p>
          </div>
          <Button
            type="button"
            size="sm"
            variant="outline"
            onClick={() => setShortcutsOpen(true)}
            aria-label="Ver atajos de teclado"
            data-testid="open-shortcuts"
          >
            <KeyboardIcon />
            Atajos
          </Button>
        </div>
        <QuestionBox
          ref={questionRef}
          disabled={loading}
          loading={loading}
          onSubmit={handleAsk}
          onCancel={() => {
            cancel()
          }}
          onHistory={questionHistory.peek}
          historyActive={questionHistory.cursor !== null}
          onPasteFiles={handleFiles}
        />
      </section>

      <Conversation
        className="min-h-[12rem] rounded-xl border border-border bg-card/60"
        data-testid="ask-conversation"
      >
        <ConversationContent className="p-4">
          {showEmpty ? (
            <ConversationEmptyState
              title="Aún no hay consulta"
              description="Elige una sugerencia o escribe tu pregunta."
            >
              <Suggestions className="mt-2 justify-center">
                {SUGGESTIONS.map((item) => (
                  <Suggestion
                    key={item}
                    suggestion={item}
                    onClick={(value) => {
                      questionRef.current?.setValue(value)
                      handleAsk(value)
                    }}
                  />
                ))}
              </Suggestions>
            </ConversationEmptyState>
          ) : null}

          {loading ? <AskLoadingSkeleton /> : null}

          {status.kind === "cancelled" ? (
            <AskErrorNotice
              error={{
                code: "cancelled",
                message: "Consulta cancelada.",
              }}
              onRetry={handleRetry}
            />
          ) : null}

          {status.kind === "error" ? (
            <AskErrorNotice error={status.error} onRetry={handleRetry} />
          ) : null}

          {status.kind === "success" && !status.data.ok ? (
            <RefusalNotice
              message={status.data.answer}
              reason={status.data.reason}
            />
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
                onRegenerate={handleRegenerate}
              />
              {viewerOpen ? (
                <SourceViewer
                  citation={selected}
                  pageImageSrc={pageImageSrc}
                  page={page}
                  pageIndex={pageIndex}
                  pageCount={pageCount}
                  onPrevPage={() =>
                    selected &&
                    setPageSel({
                      chunkId: selected.chunk_id,
                      index: Math.max(0, pageIndex - 1),
                    })
                  }
                  onNextPage={() =>
                    selected &&
                    setPageSel({
                      chunkId: selected.chunk_id,
                      index: Math.min(pageCount - 1, pageIndex + 1),
                    })
                  }
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
              ) : (
                <div
                  className="flex items-center justify-center rounded-xl border border-dashed border-border p-6 text-sm text-muted-foreground"
                  data-testid="source-viewer-closed"
                >
                  Visor cerrado. Selecciona una cita o pulsa Esc de nuevo tras
                  abrirla.
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    className="ml-3"
                    onClick={() => setViewerOpen(true)}
                  >
                    Abrir visor
                  </Button>
                </div>
              )}
            </section>
          ) : null}
        </ConversationContent>
        <ConversationScrollButton />
      </Conversation>

      {documentUpload.status.kind === "uploading" ||
      documentUpload.status.kind === "success" ||
      documentUpload.status.kind === "error" ? (
        <p className="sr-only" role="status">
          {documentUpload.status.kind === "uploading"
            ? `Subiendo ${documentUpload.status.fileName}`
            : documentUpload.status.kind === "success"
              ? "Documento indexado"
              : "Error al subir documento"}
        </p>
      ) : null}

      <DocumentUploadPanel api={documentUpload} />
      <ShortcutsHelp
        open={shortcutsOpen}
        onClose={() => setShortcutsOpen(false)}
      />
    </div>
  )
}
