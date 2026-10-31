"use client"

import Link from "next/link"

import { Suggestion, Suggestions } from "@/components/ai/suggestion"
import { RefusalNotice } from "@/components/domain/RefusalNotice"
import { ThemeControls } from "@/components/theme/theme-controls"
import { useTheme } from "@/components/theme/theme-provider"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Label } from "@/components/ui/label"
import { Progress } from "@/components/ui/progress"
import { Skeleton } from "@/components/ui/skeleton"
import { Textarea } from "@/components/ui/textarea"
import { modeLabel, themeLabel } from "@/lib/theme"

const SWATCHES = [
  "background",
  "foreground",
  "primary",
  "secondary",
  "muted",
  "accent",
  "destructive",
  "border",
  "highlight",
] as const

export default function DesignPage() {
  const { theme, mode } = useTheme()

  return (
    <main
      className="mx-auto flex w-full max-w-5xl flex-col gap-10 px-4 py-8 sm:px-6 sm:py-10"
      data-testid="design-page"
    >
      <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div className="flex flex-col gap-2">
          <p className="text-sm text-muted-foreground">
            <Link href="/" className="underline-offset-4 hover:underline">
              Doc Assistant
            </Link>
          </p>
          <h1 className="font-heading text-3xl font-semibold tracking-tight">
            Sistema de diseño
          </h1>
          <p className="max-w-2xl text-sm leading-relaxed text-muted-foreground">
            Tema activo: {themeLabel(theme)} · {modeLabel(mode)}. Los tokens
            viven en `src/themes/*.css` bajo `[data-theme]`.
          </p>
        </div>
        <ThemeControls />
      </header>

      <section className="flex flex-col gap-4" aria-labelledby="tokens-heading">
        <h2 id="tokens-heading" className="font-heading text-lg font-medium">
          Tokens de color
        </h2>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-5">
          {SWATCHES.map((name) => (
            <div key={name} className="flex flex-col gap-2">
              <div
                className="h-16 rounded-lg border border-border"
                style={{ background: `var(--${name})` }}
                data-testid={`swatch-${name}`}
              />
              <span className="font-mono text-xs text-muted-foreground">
                --{name}
              </span>
            </div>
          ))}
        </div>
      </section>

      <section className="flex flex-col gap-4" aria-labelledby="type-heading">
        <h2 id="type-heading" className="font-heading text-lg font-medium">
          Tipografía
        </h2>
        <div className="flex flex-col gap-3 rounded-xl border border-border bg-card p-5 shadow-[var(--shadow-panel)]">
          <p className="font-heading text-2xl">Titular con font-heading</p>
          <p className="text-base">Cuerpo sans para lectura de respuestas.</p>
          <p className="font-mono text-sm">chunk_id · mono para citas y IDs</p>
        </div>
      </section>

      <section
        className="flex flex-col gap-4"
        aria-labelledby="components-heading"
      >
        <h2 id="components-heading" className="font-heading text-lg font-medium">
          Componentes
        </h2>
        <div className="grid gap-4 md:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>Controles</CardTitle>
              <CardDescription>Botones, badges y campo</CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col gap-3">
              <div className="flex flex-wrap gap-2">
                <Button>Primario</Button>
                <Button variant="outline">Contorno</Button>
                <Button variant="ghost">Ghost</Button>
                <Badge>ok</Badge>
                <Badge variant="destructive">revisar</Badge>
              </div>
              <div className="flex flex-col gap-2">
                <Label htmlFor="design-demo-textarea">Pregunta de ejemplo</Label>
                <Textarea
                  id="design-demo-textarea"
                  defaultValue="Campo de pregunta de ejemplo"
                  rows={2}
                />
              </div>
              <Progress value={64} label="Subida" />
              <Skeleton className="h-8 w-full" aria-hidden />
            </CardContent>
          </Card>
          <div className="flex flex-col gap-4">
            <Alert>
              <AlertTitle>Aviso</AlertTitle>
              <AlertDescription>
                Los rechazos no usan este estilo de error.
              </AlertDescription>
            </Alert>
            <RefusalNotice
              message="No hay pasajes indexados que respondan a la consulta."
              reason="no_evidence"
            />
            <Suggestions>
              <Suggestion suggestion="Sugerencia A" onClick={() => undefined} />
              <Suggestion suggestion="Sugerencia B" onClick={() => undefined} />
            </Suggestions>
          </div>
        </div>
      </section>
    </main>
  )
}
