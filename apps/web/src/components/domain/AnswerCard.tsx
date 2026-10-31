import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { CitationChip } from "@/components/domain/CitationChip"
import type { Answer } from "@/lib/domain/types"

type AnswerCardProps = {
  answer: Answer
}

export function AnswerCard({ answer }: AnswerCardProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Respuesta</CardTitle>
        <CardDescription>{answer.question}</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <p className="text-sm leading-relaxed text-foreground">{answer.body}</p>
        {answer.citations.length > 0 ? (
          <div className="flex flex-wrap gap-2">
            {answer.citations.map((citation) => (
              <CitationChip key={citation.id} citation={citation} />
            ))}
          </div>
        ) : null}
      </CardContent>
    </Card>
  )
}
