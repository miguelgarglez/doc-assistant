"use client"

import { useId, useState, type FormEvent } from "react"

import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"

type QuestionBoxProps = {
  disabled?: boolean
  onSubmit: (question: string) => void
}

export function QuestionBox({ disabled = false, onSubmit }: QuestionBoxProps) {
  const id = useId()
  const [question, setQuestion] = useState("")

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const trimmed = question.trim()
    if (!trimmed || disabled) {
      return
    }
    onSubmit(trimmed)
  }

  return (
    <form
      className="flex flex-col gap-3"
      onSubmit={handleSubmit}
      aria-busy={disabled || undefined}
    >
      <div className="flex flex-col gap-2">
        <Label htmlFor={id}>Pregunta</Label>
        <Textarea
          id={id}
          name="question"
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          placeholder="¿Cuál es la carga útil máxima del GR-50?"
          rows={3}
          disabled={disabled}
          maxLength={1000}
          required
          aria-describedby={`${id}-hint`}
        />
        <p id={`${id}-hint`} className="text-xs leading-relaxed text-muted-foreground">
          La respuesta citará el documento, la sección y la página, o explicará
          el rechazo si no hay evidencia.
        </p>
      </div>
      <div>
        <Button type="submit" disabled={disabled || question.trim().length === 0}>
          Consultar
        </Button>
      </div>
    </form>
  )
}
