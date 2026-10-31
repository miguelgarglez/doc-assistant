import { Page, PageHeader } from "@/components/shell/page"
import { ThemeControls } from "@/components/theme/theme-controls"

export default function SettingsPage() {
  return (
    <Page className="max-w-3xl">
      <PageHeader description="Personaliza la apariencia de la aplicación." title="Ajustes" />
      <section aria-labelledby="appearance-heading" className="flex flex-col gap-4 rounded-xl border border-border bg-card p-5">
        <h2 className="font-heading text-sm font-semibold" id="appearance-heading">
          Apariencia
        </h2>
        <ThemeControls />
      </section>
    </Page>
  )
}
