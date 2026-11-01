import { Skeleton } from "@/components/ui/skeleton"

/** Placeholder lines while the answer is on its way. Decorative: the status text already says what is happening. */
export function AnswerSkeleton() {
  return (
    <div aria-hidden className="flex w-full max-w-md flex-col gap-2 pt-1" data-testid="answer-skeleton">
      <Skeleton className="h-3.5 w-full" />
      <Skeleton className="h-3.5 w-11/12" />
      <Skeleton className="h-3.5 w-2/3" />
    </div>
  )
}
