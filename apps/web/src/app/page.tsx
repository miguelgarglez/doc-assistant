import { AnswerCard } from "@/components/domain/AnswerCard"
import { InvoiceReviewCard } from "@/components/domain/InvoiceReviewCard"
import { RefusalNotice } from "@/components/domain/RefusalNotice"
import { SourceViewer } from "@/components/domain/SourceViewer"
import { UploadDropzone } from "@/components/domain/UploadDropzone"
import {
  exampleAnswer,
  exampleInvoice,
  exampleRefusal,
  exampleSources,
  exampleUploads,
} from "@/lib/domain/examples"

export default function HomePage() {
  return (
    <main className="mx-auto flex w-full max-w-5xl flex-col gap-8 px-6 py-10">
      <header className="flex flex-col gap-2">
        <p className="text-sm font-medium tracking-wide text-muted-foreground">
          tt-web
        </p>
        <h1 className="text-3xl font-semibold tracking-tight text-foreground">
          Revisión fiscal con citas
        </h1>
        <p className="max-w-2xl text-sm leading-relaxed text-muted-foreground">
          Scaffold de UI: tokens CSS, primitivos shadcn/Base UI y componentes de
          dominio con datos de ejemplo tipados.
        </p>
      </header>

      <section className="grid gap-6 lg:grid-cols-2">
        <AnswerCard answer={exampleAnswer} />
        <SourceViewer sources={exampleSources} />
      </section>

      <section className="grid gap-6 lg:grid-cols-2">
        <InvoiceReviewCard invoice={exampleInvoice} />
        <UploadDropzone files={exampleUploads} />
      </section>

      <section>
        <RefusalNotice refusal={exampleRefusal} />
      </section>
    </main>
  )
}
