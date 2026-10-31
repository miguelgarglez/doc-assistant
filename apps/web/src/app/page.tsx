import { AskWorkspace } from "@/components/domain/AskWorkspace"

export default function HomePage() {
  return (
    <main className="mx-auto flex w-full max-w-6xl flex-col gap-8 px-4 py-8 sm:px-6 sm:py-10">
      <header className="flex flex-col gap-3">
        <h1 className="text-3xl font-semibold tracking-tight text-foreground sm:text-4xl">
          Doc Assistant
        </h1>
        <p className="max-w-2xl text-base leading-relaxed text-muted-foreground">
          Pregunta sobre fichas técnicas, manuales de instalación, de célula o
          de visión. Las respuestas citan el fragmento exacto o rechazan si no
          hay evidencia indexada.
        </p>
      </header>

      <AskWorkspace />
    </main>
  )
}
