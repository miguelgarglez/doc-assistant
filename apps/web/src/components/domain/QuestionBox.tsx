"use client"

import {
  useEffect,
  useId,
  useImperativeHandle,
  useRef,
  useState,
  type FormEvent,
  type KeyboardEvent,
  type Ref,
} from "react"
import { SquareIcon } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { isModKey } from "@/lib/shortcuts"
import { cn } from "@/lib/utils"

export type QuestionBoxHandle = {
  focus: () => void
  setValue: (value: string) => void
  value: () => string
}

type QuestionBoxProps = {
  disabled?: boolean
  loading?: boolean
  onSubmit: (question: string) => void
  onCancel?: () => void
  historyActive?: boolean
  onHistory?: (direction: "up" | "down") => string | null
  onPasteFiles?: (files: File[]) => void
  ref?: Ref<QuestionBoxHandle>
}

export function QuestionBox({
  disabled = false,
  loading = false,
  onSubmit,
  onCancel,
  onHistory,
  historyActive = false,
  onPasteFiles,
  ref,
}: QuestionBoxProps) {
  const id = useId()
  const [question, setQuestion] = useState("")
  const composingRef = useRef(false)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useImperativeHandle(ref, () => ({
    focus: () => textareaRef.current?.focus(),
    setValue: (value: string) => setQuestion(value),
    value: () => question,
  }))

  useEffect(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = "auto"
    el.style.height = `${Math.min(el.scrollHeight, 180)}px`
  }, [question])

  function submit() {
    const trimmed = question.trim()
    if (!trimmed || disabled || loading) {
      return
    }
    onSubmit(trimmed)
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    submit()
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (composingRef.current || event.nativeEvent.isComposing || event.nativeEvent.keyCode === 229) return
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault()
      submit()
      return
    }
    if (event.key === "Enter" && isModKey(event)) {
      event.preventDefault()
      submit()
      return
    }
    if (
      onHistory &&
      (event.key === "ArrowUp" || event.key === "ArrowDown") &&
      (question.trim().length === 0 || historyActive) &&
      !event.shiftKey &&
      !isModKey(event)
    ) {
      event.preventDefault()
      const next = onHistory(event.key === "ArrowUp" ? "up" : "down")
      if (next !== null) {
        setQuestion(next)
      }
    }
  }

  return (
    <form
      className="flex flex-col gap-3"
      onSubmit={handleSubmit}
      aria-busy={loading || undefined}
      data-testid="question-box"
      onDragOver={(event) => {
        event.preventDefault()
      }}
      onDrop={(event) => {
        event.preventDefault()
        const files = Array.from(event.dataTransfer.files)
        if (files.length > 0) {
          onPasteFiles?.(files)
        }
      }}
    >
      <div className="flex flex-col gap-2">
        <div className="flex items-center justify-between gap-2">
          <Label htmlFor={id}>Pregunta</Label>
          <span className="text-xs text-muted-foreground">
            Enter envía · Shift+Enter línea
          </span>
        </div>
        <Textarea
          ref={textareaRef}
          id={id}
          name="question"
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          onKeyDown={handleKeyDown}
          onCompositionStart={() => { composingRef.current = true }}
          onCompositionEnd={() => { composingRef.current = false }}
          onPaste={(event) => {
            const files = Array.from(event.clipboardData.files)
            if (files.length > 0) {
              event.preventDefault()
              onPasteFiles?.(files)
            }
          }}
          placeholder="Pregunta sobre la documentación indexada…"
          rows={3}
          disabled={disabled && !loading}
          maxLength={1000}
          required
          aria-describedby={`${id}-hint`}
          className={cn(
            "min-h-[4.5rem] resize-none transition-[height] duration-[var(--duration-fast)] ease-[var(--ease-out)]"
          )}
          data-testid="question-input"
        />
        <p id={`${id}-hint`} className="sr-only">
          La respuesta citará el documento y la página, o explicará el rechazo.
        </p>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        {loading ? (
          <Button
            type="button"
            variant="outline"
            onClick={(event) => {
              event.preventDefault()
              event.stopPropagation()
              onCancel?.()
            }}
            data-testid="cancel-ask"
          >
            <SquareIcon />
            Cancelar
          </Button>
        ) : (
          <Button
            type="submit"
            disabled={disabled || question.trim().length === 0}
            className="active:scale-[0.97] motion-reduce:active:scale-100"
          >
            Consultar
          </Button>
        )}
      </div>
    </form>
  )
}
