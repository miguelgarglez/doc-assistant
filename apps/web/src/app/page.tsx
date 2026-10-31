import { AskWorkspace } from "@/components/domain/AskWorkspace"

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
          Consulta el corpus indexado. Las respuestas citan fragmentos
          verificados o explican el rechazo.
        </p>
      </header>

      <AskWorkspace />
    </main>
  )
}
