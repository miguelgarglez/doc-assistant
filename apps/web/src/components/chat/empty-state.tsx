"use client"

import { FileSearchIcon, PlusIcon } from "lucide-react"

import { Suggestion, Suggestions } from "@/components/ai-elements/suggestion"
import { useAddSources } from "@/features/uploads"
import { useSources } from "@/features/sources"
import { Button } from "@/components/ui/button"
import type { Source } from "@/lib/api/types"

/** Suggestions come from what is indexed, so they are never about documents that do not exist. */
export function suggestionsFor(sources: readonly Source[]): string[] {
  const documents = sources.filter((source) => source.kind === "pdf")
  const questions = documents.slice(0, 2).map((source) => `¿De qué trata ${source.title ?? source.name}?`)
  if (documents.length > 1) questions.push("¿Qué diferencias hay entre los documentos?")
  if (sources.some((source) => source.kind === "invoice")) questions.push("¿Qué facturas tengo indexadas?")
  return questions.slice(0, 4)
}

export function EmptyState({ onAsk }: { onAsk: (question: string) => void }) {
  const sources = useSources()
  const addSources = useAddSources()
  const ready = sources.status === "ready"
  const suggestions = suggestionsFor(sources.items)
  const count = sources.items.length

  return (
    <div className="mx-auto flex min-h-full w-full max-w-2xl flex-col items-center justify-center gap-6 px-4 py-10 text-center" data-testid="chat-empty">
      <span className="flex size-12 items-center justify-center rounded-2xl border border-border bg-card text-primary shadow-sm">
        <FileSearchIcon className="size-6" />
      </span>
      <div className="flex flex-col gap-2">
        <h2 className="font-heading text-2xl font-semibold tracking-tight text-balance">
          Pregunta sobre tus documentos
        </h2>
        <p className="mx-auto max-w-md text-sm text-muted-foreground text-pretty">
          {!ready
            ? "Comprobando las fuentes indexadas…"
            : count === 0
              ? "Añade un PDF o una imagen de factura y pregunta lo que necesites. Cada respuesta cita el fragmento del que sale."
              : "Cada respuesta cita el fragmento del que sale. Si las fuentes no lo respaldan, no se inventa nada."}
        </p>
      </div>
      {ready && suggestions.length > 0 ? (
        <Suggestions className="flex-wrap justify-center" aria-label="Preguntas sugeridas">
          {suggestions.map((question) => (
            <Suggestion key={question} onClick={onAsk} suggestion={question} />
          ))}
        </Suggestions>
      ) : null}
      {ready && count === 0 ? (
        <Button data-testid="empty-add-source" onClick={() => addSources.setOpen(true)} size="lg" type="button">
          <PlusIcon data-icon="inline-start" />
          Añadir fuentes
        </Button>
      ) : null}
    </div>
  )
}
