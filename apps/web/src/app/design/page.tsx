"use client"

import { Attachment, AttachmentInfo, AttachmentPreview, AttachmentRemove, AttachmentStatusIcon, Attachments } from "@/components/ai-elements/attachments"
import { Message, MessageContent, MessageResponse } from "@/components/ai-elements/message"
import { Shimmer } from "@/components/ai-elements/shimmer"
import { Suggestion, Suggestions } from "@/components/ai-elements/suggestion"
import { Refusal } from "@/components/chat/assistant-message"
import { Citations } from "@/components/chat/citations"
import { TraceBlock } from "@/components/chat/trace-block"
import { Page, PageHeader } from "@/components/shell/page"
import { StatusBadge } from "@/components/sources/status-badge"
import { ThemeControls } from "@/components/theme/theme-controls"
import { useTheme } from "@/components/theme/theme-provider"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import type { Citation, StepData } from "@/lib/chat/types"
import { modeLabel, themeLabel } from "@/lib/theme"

const SWATCHES = ["background", "foreground", "primary", "secondary", "muted", "accent", "destructive", "border", "highlight"] as const

const CITATIONS: Citation[] = [
  { chunk_id: "demo-1", quote: "Alcance de detección: 4 m.", doc: "sensor-demo", doc_id: "pdf-demo", section: "2", pages: [1], fragment: "Alcance de detección: 4 m." },
  { chunk_id: "demo-2", quote: "Temperatura de trabajo: 0 a 50 °C.", doc: "sensor-demo", doc_id: "pdf-demo", section: "3", pages: [1], fragment: "Temperatura de trabajo: 0 a 50 °C." },
]

const STEPS: StepData[] = [
  { id: "retrieve", status: "done", label: "Buscando fragmentos relevantes", elapsed_s: 0.31, data: {} },
  { id: "generate", status: "done", label: "Respuesta redactada", elapsed_s: 1.84, data: {} },
  { id: "verify", status: "done", label: "Citas verificadas contra los fragmentos", elapsed_s: 0.02, data: {} },
]

function Section({ id, title, children }: { id: string; title: string; children: React.ReactNode }) {
  return (
    <section aria-labelledby={id} className="flex flex-col gap-3">
      <h2 className="font-heading text-sm font-semibold" id={id}>
        {title}
      </h2>
      {children}
    </section>
  )
}

export default function DesignPage() {
  const { theme, mode } = useTheme()
  return (
    <Page className="max-w-4xl gap-8" >
      <PageHeader
        actions={<ThemeControls />}
        description={`Tema activo: ${themeLabel(theme)} · ${modeLabel(mode)}. Los tokens viven en src/themes/*.css bajo [data-theme].`}
        title="Sistema de diseño"
      />
      <div data-testid="design-page" className="flex flex-col gap-8">
        <Section id="tokens-heading" title="Tokens de color">
          <div className="grid grid-cols-3 gap-3 sm:grid-cols-5 md:grid-cols-9">
            {SWATCHES.map((name) => (
              <div className="flex flex-col gap-1.5" key={name}>
                <div className="h-12 rounded-lg border border-border" data-testid={`swatch-${name}`} style={{ background: `var(--${name})` }} />
                <span className="font-mono text-[0.6875rem] text-muted-foreground">--{name}</span>
              </div>
            ))}
          </div>
        </Section>

        <Section id="type-heading" title="Tipografía">
          <div className="flex flex-col gap-2 rounded-xl border border-border bg-card p-4">
            <p className="font-heading text-2xl">Titular con font-heading</p>
            <p className="text-base">Cuerpo sans para lectura de respuestas.</p>
            <p className="font-mono text-sm">chunk_id · mono para citas e identificadores</p>
          </div>
        </Section>

        <Section id="chat-heading" title="Mensajes">
          <div className="flex flex-col gap-6 rounded-xl border border-border bg-card p-4">
            <Message from="user">
              <MessageContent>¿Qué alcance tiene el sensor?</MessageContent>
            </Message>
            <Message from="assistant">
              <MessageContent>
                <TraceBlock live={false} steps={STEPS} total={2.17} />
                <MessageResponse>{"El alcance de detección es de **4 m** y trabaja entre 0 y 50 °C."}</MessageResponse>
                <Citations activeIndex={null} citations={CITATIONS} onOpen={() => undefined} />
              </MessageContent>
            </Message>
            <Message from="assistant">
              <MessageContent>
                <p className="text-sm">
                  <Shimmer>Verificando con las fuentes…</Shimmer>
                </p>
              </MessageContent>
            </Message>
            <Refusal
              onAsk={() => undefined}
              refusal={{ answer: "No dispongo de esa información en los documentos.", reason: "no_evidence", suggestions: [] }}
            />
            <Alert variant="destructive">
              <AlertTitle>No se pudo completar la consulta</AlertTitle>
              <AlertDescription>El servicio no responde.</AlertDescription>
            </Alert>
          </div>
        </Section>

        <Section id="inputs-heading" title="Adjuntos y sugerencias">
          <div className="flex flex-col gap-4 rounded-xl border border-border bg-card p-4">
            <Attachments>
              {(["uploading", "processing", "done", "error"] as const).map((status) => (
                <Attachment
                  data={{ id: status, filename: "manual-demo.pdf", mediaType: "application/pdf", status, progress: 42, detail: "Tipo no admitido" }}
                  key={status}
                  onRemove={() => undefined}
                >
                  <AttachmentPreview />
                  <AttachmentInfo />
                  <AttachmentStatusIcon />
                  <AttachmentRemove />
                </Attachment>
              ))}
            </Attachments>
            <Suggestions>
              <Suggestion suggestion="Sugerencia A" />
              <Suggestion suggestion="Sugerencia B" />
            </Suggestions>
            <div className="flex flex-wrap items-center gap-2">
              <Button>Primario</Button>
              <Button variant="outline">Contorno</Button>
              <Button variant="ghost">Ghost</Button>
              <StatusBadge status="indexed" />
              <StatusBadge status="review" />
              <StatusBadge status="no_text" />
            </div>
            <Skeleton aria-hidden className="h-8 w-full" />
          </div>
        </Section>
      </div>
    </Page>
  )
}
