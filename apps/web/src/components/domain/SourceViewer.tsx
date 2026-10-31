import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Separator } from "@/components/ui/separator"
import type { SourceDocument } from "@/lib/domain/types"

type SourceViewerProps = {
  sources: readonly SourceDocument[]
}

export function SourceViewer({ sources }: SourceViewerProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Fuentes</CardTitle>
        <CardDescription>
          Fragmentos recuperados para la respuesta actual.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-56 pr-3">
          <div className="flex flex-col gap-4">
            {sources.map((source, index) => (
              <div key={source.id} className="flex flex-col gap-2">
                {index > 0 ? <Separator /> : null}
                <div className="flex flex-col gap-1">
                  <p className="text-sm font-medium text-foreground">
                    {source.title}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {source.pageCount} páginas
                  </p>
                  <p className="text-sm leading-relaxed text-muted-foreground">
                    {source.excerpt}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  )
}
