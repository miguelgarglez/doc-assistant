import { ThemeControls } from "@/components/theme/theme-controls"

export default function SettingsPage() {
  return <main className="mx-auto flex w-full max-w-6xl flex-col gap-6 px-4 py-8 sm:px-6"><div><h1 className="font-heading text-3xl font-semibold">Ajustes</h1><p className="mt-2 text-muted-foreground">Personaliza la apariencia de la aplicación.</p></div><section className="rounded-xl border border-border bg-card p-6"><h2 className="mb-4 font-heading text-lg font-medium">Apariencia</h2><ThemeControls /></section></main>
}
