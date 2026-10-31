"use client"

import { useEffect, useLayoutEffect, useRef, useState } from "react"
import Link from "next/link"
import { useTrace } from "@/components/system/trace-provider"
import { KeyboardIcon } from "lucide-react"

import {
  Conversation,
  ConversationContent,
  ConversationEmptyState,
  ConversationScrollButton,
} from "@/components/ai/conversation"
import { Trace, TraceLine, TraceTitle } from "@/components/ai/trace"
import { Message, MessageContent } from "@/components/ai/message"
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
import { useAsk, type AskStatus } from "@/hooks/use-ask"
import { useDocumentUpload } from "@/hooks/use-document-upload"
import { useQuestionHistory } from "@/hooks/use-question-history"
import { citationPage, sourcePageUrl } from "@/lib/api/source-url"
import {
  classifyDroppedFile,
} from "@/lib/api/upload"
import type { Citation } from "@/lib/api/types"
import { isEditableTarget, isModKey } from "@/lib/shortcuts"

const SUGGESTIONS = [
  "¿Cuáles son los puntos principales de las fuentes?",
  "¿Qué datos técnicos aparecen en los documentos?",
  "Resume la información disponible.",
] as const

export function AskWorkspace({ onInvoice }: { onInvoice: (file: File) => Promise<void> }) {
  const { status, ask, cancel } = useAsk()
  const trace = useTrace()
  const [archiveCitation, setArchiveCitation] = useState<Citation | null>(null)
  const [archivePage, setArchivePage] = useState(0)
  const questionHistory = useQuestionHistory()
  const documentUpload = useDocumentUpload()
  const { toast } = useToast()
  const questionRef = useRef<QuestionBoxHandle>(null)
  const [previous, setPrevious] = useState<Exclude<AskStatus, { kind: "idle" } | { kind: "loading" }>[]>([])
  const [selectedIndex, setSelectedIndex] = useState(0)
  const [shortcutsOpen, setShortcutsOpen] = useState(false)
  const [viewerOpen, setViewerOpen] = useState(true)

  useEffect(() => {
    if (status.kind === "error" && !questionRef.current?.value()) {
      questionRef.current?.setValue(status.question)
    }
  }, [status])

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
    if (status.kind !== "idle" && status.kind !== "loading") {
      setPrevious((items) => [...items, status])
    }
    questionRef.current?.setValue("")
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
    <div className="flex flex-col gap-4" onDragOver={(event) => event.preventDefault()} onDrop={(event) => { event.preventDefault(); handleFiles(Array.from(event.dataTransfer.files)) }}>
      <section aria-labelledby="ask-heading" className="flex flex-col gap-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="flex flex-col gap-1">
            <h2
              id="ask-heading"
              className="font-heading text-lg font-medium text-foreground"
            >
              Chat
            </h2>
            <p className="max-w-2xl text-sm leading-relaxed text-muted-foreground">
              Pregunta sobre tus fuentes y revisa las citas.
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

      </section>

      <Conversation
        className="h-[min(70vh,48rem)] min-h-[12rem] rounded-xl border border-border bg-card/60"
        data-testid="ask-conversation"
      >
        <ConversationContent className="p-4">
          {showEmpty ? (
            <ConversationEmptyState
              title="Aún no hay consulta"
              description="Elige una sugerencia o escribe tu pregunta."
            >
              <div><h3 className="font-heading text-xl font-medium">¿Qué quieres saber?</h3><p className="mt-1 text-sm text-muted-foreground">Elige una sugerencia o escribe una pregunta.</p><Link href="/fuentes" className="mt-3 inline-block text-sm text-foreground underline">Añadir fuentes</Link></div>
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

          {previous.map((item, index) => (
            <div key={index} className="flex flex-col gap-3" data-testid="previous-turn">
              {item.kind === "success" && item.data.ok ? (
                <AnswerCard
                  question={item.question}
                  answer={item.data.answer}
                  citations={item.data.citations}
                  onSelectCitation={(citation) => { setArchiveCitation(citation); setArchivePage(0) }}
                />
              ) : item.kind === "success" ? (
                <><p>{item.question}</p><RefusalNotice message={item.data.answer} reason={item.data.reason} /></>
              ) : (
                <><p>{item.question}</p><p className="text-sm text-muted-foreground">{item.kind === "error" ? item.error.message : "Consulta cancelada."}</p></>
              )}
            </div>
          ))}

          {archiveCitation ? <SourceViewer citation={archiveCitation} page={citationPage(archiveCitation, archivePage) ?? null} pageImageSrc={citationPage(archiveCitation, archivePage) != null ? sourcePageUrl(archiveCitation.doc_id, citationPage(archiveCitation, archivePage)!) : null} pageIndex={archivePage} pageCount={archiveCitation.pages.length} onPrevPage={() => setArchivePage((index) => Math.max(0, index - 1))} onNextPage={() => setArchivePage((index) => Math.min(archiveCitation.pages.length - 1, index + 1))} /> : null}
          {loading ? <div className="flex flex-col gap-3"><p className="rounded-lg bg-muted p-3">{status.question}</p>{trace.steps.length ? <Trace aria-label="Pasos de la consulta">{trace.steps.filter((step, index, all) => all.findLastIndex((item) => item.id === step.id) === index).map((step) => <TraceLine key={step.id} status={step.status === "running" ? "running" : undefined}><TraceTitle>{step.label}{step.status === "done" ? " ✓" : "…"}</TraceTitle></TraceLine>)}</Trace> : <AskLoadingSkeleton />}{status.text ? <div aria-live="polite" className="rounded-lg border border-border p-4"><p className="mb-2 text-xs text-muted-foreground">Respuesta provisional. Verificando fuentes…</p><p className="whitespace-pre-wrap">{status.text}</p></div> : null}</div> : null}

          {status.kind !== "idle" && status.kind !== "loading" && (status.kind !== "success" || !status.data.ok) ? <Message align="end"><MessageContent><p className="w-fit max-w-[85%] rounded-xl bg-muted px-4 py-3">{status.question}</p></MessageContent></Message> : null}
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

          {status.kind === "success" && trace.steps.length ? <details className="text-sm text-muted-foreground"><summary className="cursor-pointer">Ver pasos de la consulta</summary><Trace className="mt-2">{trace.steps.filter((step, index, all) => all.findLastIndex((item) => item.id === step.id) === index).map((step) => <TraceLine key={step.id}><TraceTitle>{step.label}</TraceTitle></TraceLine>)}</Trace></details> : null}

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

      <div className="sticky bottom-0 z-10 rounded-xl border border-border bg-background p-4 shadow-[var(--shadow-panel)]">
        <QuestionBox
          ref={questionRef}
          disabled={loading}
          loading={loading}
          onSubmit={handleAsk}
          onCancel={() => {
            if (status.kind === "loading") questionRef.current?.setValue(status.question)
            cancel()
          }}
          onHistory={questionHistory.peek}
          historyActive={questionHistory.cursor !== null}
          onPasteFiles={handleFiles}
        />
      </div>

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

      {documentUpload.status.kind !== "idle" ? <DocumentUploadPanel api={documentUpload} /> : null}
      <ShortcutsHelp
        open={shortcutsOpen}
        onClose={() => setShortcutsOpen(false)}
      />
    </div>
  )
}
