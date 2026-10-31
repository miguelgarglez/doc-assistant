import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { CitationChips } from "@/components/domain/CitationChips"
import type { Citation } from "@/lib/api/types"

type AnswerCardProps = {
  question: string
  answer: string
  citations: readonly Citation[]
  selectedChunkId?: string | null
  onSelectCitation: (citation: Citation) => void
}

export function AnswerCard({
  question,
  answer,
  citations,
  selectedChunkId = null,
  onSelectCitation,
}: AnswerCardProps) {
  return (
    <Card data-testid="answer-card">
      <CardHeader>
        <CardTitle>Respuesta</CardTitle>
        <CardDescription className="text-sm leading-relaxed">
          {question}
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-5">
        <p className="text-sm leading-relaxed text-foreground sm:text-[0.95rem]">
          {answer}
        </p>
        <CitationChips
          citations={citations}
          selectedChunkId={selectedChunkId}
          onSelect={onSelectCitation}
        />
      </CardContent>
    </Card>
  )
}
