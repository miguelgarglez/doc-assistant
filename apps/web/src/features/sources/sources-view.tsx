"use client"

import { ArrowDownIcon, ArrowUpIcon, FileTextIcon, ReceiptTextIcon, PlusIcon, SearchIcon } from "lucide-react"
import { useMemo, useState } from "react"
import { toast } from "sonner"

import { useAddSources } from "@/components/providers/add-sources-provider"
import { useSources } from "@/features/sources/sources-provider"
import { Page, PageHeader } from "@/components/shell/page"
import { SourceDetail } from "@/features/sources/source-detail"
import { KindLabel, StatusBadge } from "@/features/sources/status-badge"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Sheet, SheetContent, SheetDescription, SheetTitle } from "@/components/ui/sheet"
import { Skeleton } from "@/components/ui/skeleton"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { useMediaQuery } from "@/hooks/use-media-query"
import type { Source } from "@/lib/api/types"
import { cn } from "@/lib/utils"

type Filter = "all" | Source["kind"]
type SortKey = "name" | "added"

const FILTERS: readonly [Filter, string][] = [
  ["all", "Todas"],
  ["pdf", "Documentos"],
  ["invoice", "Facturas"],
]

function dateLabel(value: string | null | undefined) {
  if (!value) return "—"
  return new Date(value).toLocaleDateString("es-ES", { day: "numeric", month: "short", year: "numeric" })
}

export function SourcesView() {
  const sources = useSources()
  const addSources = useAddSources()
  const [filter, setFilter] = useState<Filter>("all")
  const [query, setQuery] = useState("")
  const [sort, setSort] = useState<{ key: SortKey; dir: "asc" | "desc" }>({ key: "added", dir: "desc" })
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [pendingRemoval, setPendingRemoval] = useState<Source | null>(null)
  const [removing, setRemoving] = useState(false)
  const wide = useMediaQuery("(min-width: 1024px)")

  const counts = useMemo(
    () => ({
      all: sources.items.length,
      pdf: sources.items.filter((item) => item.kind === "pdf").length,
      invoice: sources.items.filter((item) => item.kind === "invoice").length,
    }),
    [sources.items]
  )

  const rows = useMemo(() => {
    const needle = query.trim().toLowerCase()
    const filtered = sources.items.filter(
      (item) =>
        (filter === "all" || item.kind === filter) &&
        (!needle || `${item.name} ${item.title ?? ""}`.toLowerCase().includes(needle))
    )
    const factor = sort.dir === "asc" ? 1 : -1
    return [...filtered].sort((a, b) =>
      sort.key === "name"
        ? factor * (a.title ?? a.name).localeCompare(b.title ?? b.name, "es")
        : factor * (a.added_at ?? "").localeCompare(b.added_at ?? "")
    )
  }, [sources.items, filter, query, sort])

  const selected = sources.items.find((item) => item.id === selectedId) ?? null

  const toggleSort = (key: SortKey) =>
    setSort((current) => (current.key === key ? { key, dir: current.dir === "asc" ? "desc" : "asc" } : { key, dir: key === "name" ? "asc" : "desc" }))

  const confirmRemoval = async () => {
    if (!pendingRemoval) return
    setRemoving(true)
    const error = await sources.remove(pendingRemoval.id)
    setRemoving(false)
    if (error) {
      toast(error.message)
      return
    }
    toast(`Se quitó ${pendingRemoval.name} del índice`)
    if (selectedId === pendingRemoval.id) setSelectedId(null)
    setPendingRemoval(null)
  }

  const detail = selected ? (
    <SourceDetail
      key={selected.id}
      onClose={() => setSelectedId(null)}
      onRemove={() => setPendingRemoval(selected)}
      source={selected}
    />
  ) : null

  const sortIcon = (key: SortKey) =>
    sort.key !== key ? null : sort.dir === "asc" ? <ArrowUpIcon className="size-3" /> : <ArrowDownIcon className="size-3" />

  return (
    <div className="flex min-h-0 flex-1">
      <Page className="min-w-0 lg:min-h-0">
        <PageHeader
          description="Documentos y facturas que el asistente puede citar."
          actions={
            <Button data-testid="upload-trigger" onClick={() => addSources.setOpen(true)} size="lg" type="button">
              <PlusIcon data-icon="inline-start" />
              Añadir fuentes
            </Button>
          }
          title="Fuentes"
        />
        <section aria-label="Fuentes indexadas" className="flex min-h-0 flex-1 flex-col gap-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div aria-label="Filtrar por tipo" className="inline-flex items-center gap-1 rounded-lg border border-border bg-card p-1" role="group">
              {FILTERS.map(([id, label]) => (
                <Button
                  aria-pressed={filter === id}
                  data-testid={`filter-${id}`}
                  key={id}
                  onClick={() => setFilter(id)}
                  size="sm"
                  type="button"
                  variant={filter === id ? "secondary" : "ghost"}
                >
                  {label}
                  <span className="tabular-nums text-muted-foreground">{counts[id]}</span>
                </Button>
              ))}
            </div>
            <div className="relative w-full sm:w-64">
              <SearchIcon aria-hidden className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                aria-label="Buscar fuentes por nombre"
                className="pl-8"
                onChange={(event) => setQuery(event.currentTarget.value)}
                placeholder="Buscar por nombre"
                type="search"
                value={query}
              />
            </div>
          </div>

          <div className="min-h-0 flex-1 overflow-auto rounded-xl border border-border bg-card" data-testid="sources-table">
            {sources.status === "loading" ? (
              <div className="flex flex-col gap-2 p-3">
                <Skeleton className="h-9 w-full" />
                <Skeleton className="h-9 w-full" />
                <Skeleton className="h-9 w-full" />
              </div>
            ) : sources.status === "error" && sources.items.length === 0 ? (
              <div className="flex flex-col items-start gap-2 p-4 text-sm" role="alert">
                <p>No se pudieron cargar las fuentes: {sources.error.message}</p>
                <Button onClick={() => void sources.refresh()} size="sm" type="button" variant="outline">
                  Reintentar
                </Button>
              </div>
            ) : rows.length === 0 ? (
              <p className="p-4 text-sm text-muted-foreground" data-testid="sources-empty">
                {sources.items.length === 0
                  ? "Todavía no hay fuentes. Añade un PDF o una factura para empezar."
                  : "Ninguna fuente coincide con el filtro."}
              </p>
            ) : (
              <Table>
                <TableHeader className="sticky top-0 z-10 bg-card">
                  <TableRow>
                    <TableHead aria-sort={sort.key === "name" ? (sort.dir === "asc" ? "ascending" : "descending") : "none"}>
                      <button className="inline-flex cursor-pointer items-center gap-1 font-medium" onClick={() => toggleSort("name")} type="button">
                        Nombre {sortIcon("name")}
                      </button>
                    </TableHead>
                    <TableHead className="hidden sm:table-cell">Tipo</TableHead>
                    <TableHead className="hidden text-right md:table-cell">Páginas</TableHead>
                    <TableHead className="hidden text-right md:table-cell">Fragmentos</TableHead>
                    <TableHead>Estado</TableHead>
                    <TableHead
                      aria-sort={sort.key === "added" ? (sort.dir === "asc" ? "ascending" : "descending") : "none"}
                      className="hidden text-right lg:table-cell xl:table-cell"
                    >
                      <button className="inline-flex cursor-pointer items-center gap-1 font-medium" onClick={() => toggleSort("added")} type="button">
                        Añadida {sortIcon("added")}
                      </button>
                    </TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {rows.map((source) => {
                    const Icon = source.kind === "pdf" ? FileTextIcon : ReceiptTextIcon
                    const active = source.id === selectedId
                    return (
                      <TableRow
                        className={cn("cursor-pointer", active && "bg-muted")}
                        data-state={active ? "selected" : undefined}
                        data-testid="source-row"
                        key={source.id}
                        onClick={() => setSelectedId(source.id)}
                      >
                        <TableCell className="max-w-0 min-w-48">
                          <button
                            aria-pressed={active}
                            className="flex w-full min-w-0 cursor-pointer items-center gap-2.5 rounded-sm text-left outline-none focus-visible:ring-2 focus-visible:ring-ring/50"
                            onClick={(event) => {
                              event.stopPropagation()
                              setSelectedId(source.id)
                            }}
                            type="button"
                          >
                            <Icon aria-hidden className="size-4 shrink-0 text-muted-foreground" />
                            <span className="flex min-w-0 flex-col">
                              <span className="truncate text-sm font-medium">{source.title ?? source.name}</span>
                              {source.title ? <span className="truncate font-mono text-xs text-muted-foreground">{source.name}</span> : null}
                            </span>
                          </button>
                        </TableCell>
                        <TableCell className="hidden sm:table-cell">
                          <KindLabel kind={source.kind} />
                        </TableCell>
                        <TableCell className="hidden text-right tabular-nums md:table-cell">{source.n_pages}</TableCell>
                        <TableCell className="hidden text-right tabular-nums md:table-cell">{source.n_chunks}</TableCell>
                        <TableCell>
                          <StatusBadge status={source.status} />
                        </TableCell>
                        <TableCell className="hidden text-right text-xs whitespace-nowrap text-muted-foreground lg:table-cell">
                          {dateLabel(source.added_at)}
                        </TableCell>
                      </TableRow>
                    )
                  })}
                </TableBody>
              </Table>
            )}
          </div>
        </section>
      </Page>

      {detail && wide ? (
        <aside aria-label="Detalle de la fuente" className="hidden w-[24rem] shrink-0 border-l border-border lg:block xl:w-[26rem]">
          {detail}
        </aside>
      ) : null}
      {!wide ? (
        <Sheet open={selected !== null} onOpenChange={(open) => !open && setSelectedId(null)}>
          <SheetContent className="h-[85dvh] gap-0 rounded-t-xl p-0" showCloseButton={false} side="bottom">
            <SheetTitle className="sr-only">Detalle de la fuente</SheetTitle>
            <SheetDescription className="sr-only">Fragmentos y página original de la fuente seleccionada.</SheetDescription>
            {detail}
          </SheetContent>
        </Sheet>
      ) : null}

      <Dialog open={pendingRemoval !== null} onOpenChange={(open) => !open && !removing && setPendingRemoval(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Quitar «{pendingRemoval?.name}» del índice</DialogTitle>
            <DialogDescription>
              Se borran sus fragmentos y el asistente dejará de citarla. El archivo original se aparta en una carpeta del servicio, no se elimina.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button disabled={removing} onClick={() => setPendingRemoval(null)} type="button" variant="outline">
              Cancelar
            </Button>
            <Button data-testid="confirm-remove" disabled={removing} onClick={() => void confirmRemoval()} type="button" variant="destructive">
              Quitar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
