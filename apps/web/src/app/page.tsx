"use client"

import Link from "next/link"
import { useState } from "react"

import { AskWorkspace } from "@/components/domain/AskWorkspace"
import { InvoicesWorkspace } from "@/components/domain/InvoicesWorkspace"
import { ThemeControls } from "@/components/theme/theme-controls"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"

export default function HomePage() {
  const [tab, setTab] = useState("consulta")

  return (
    <main className="mx-auto flex w-full max-w-6xl flex-col gap-8 px-4 py-8 sm:px-6 sm:py-10">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div className="flex flex-col gap-2">
          <h1 className="font-heading text-3xl font-semibold tracking-tight text-foreground sm:text-4xl">
            Doc Assistant
          </h1>
          <p className="max-w-2xl text-base leading-relaxed text-muted-foreground">
            Pregunta sobre fichas técnicas y manuales. Las respuestas citan el
            fragmento exacto o rechazan si no hay evidencia.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <ThemeControls compact />
          <Link
            href="/design"
            className="text-sm text-muted-foreground underline-offset-4 hover:text-foreground hover:underline"
          >
            Diseño
          </Link>
        </div>
      </header>

      <Tabs value={tab} onValueChange={(value) => setTab(String(value))}>
        <TabsList aria-label="Secciones">
          <TabsTrigger value="consulta">Consulta</TabsTrigger>
          <TabsTrigger value="facturas">Facturas</TabsTrigger>
        </TabsList>
        <TabsContent value="consulta" className="pt-6">
          <AskWorkspace />
        </TabsContent>
        <TabsContent value="facturas" className="pt-6">
          {tab === "facturas" ? <InvoicesWorkspace /> : null}
        </TabsContent>
      </Tabs>
    </main>
  )
}
