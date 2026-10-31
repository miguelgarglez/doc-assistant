"use client"

import type { Invoice } from "@/lib/api/types"
import { displayField, formatAmountEs } from "@/lib/domain/format-amount"
import { cn } from "@/lib/utils"

type InvoiceListProps = {
  invoices: readonly Invoice[]
  selectedNumero: string | null
  onSelect: (invoice: Invoice) => void
  loading?: boolean
}

export function InvoiceList({
  invoices,
  selectedNumero,
  onSelect,
  loading = false,
}: InvoiceListProps) {
  if (loading) {
    return (
      <p className="text-sm text-muted-foreground" role="status">
        Cargando facturas…
      </p>
    )
  }

  if (invoices.length === 0) {
    return (
      <p
        className="text-sm text-muted-foreground"
        data-testid="invoice-list-empty"
        role="status"
      >
        Aún no hay facturas indexadas.
      </p>
    )
  }

  return (
    <ul
      className="flex flex-col gap-1"
      data-testid="invoice-list"
      aria-label="Facturas indexadas"
    >
      {invoices.map((invoice) => {
        const selected = invoice.numero === selectedNumero
        return (
          <li key={invoice.numero}>
            <button
              type="button"
              onClick={() => onSelect(invoice)}
              aria-pressed={selected}
              className={cn(
                "flex w-full items-baseline justify-between gap-3 rounded-md border px-3 py-2 text-left text-sm outline-none transition-colors focus-visible:ring-3 focus-visible:ring-ring/50",
                selected
                  ? "border-primary bg-muted/60"
                  : "border-border bg-card hover:bg-muted/40"
              )}
              data-testid={`invoice-list-item-${invoice.numero}`}
            >
              <span className="min-w-0 truncate">
                <span className="font-mono font-medium text-foreground">
                  {invoice.numero}
                </span>
                <span className="text-muted-foreground">
                  {" · "}
                  {displayField(invoice.emisor)}
                </span>
              </span>
              <span className="shrink-0 tabular-nums text-muted-foreground">
                {formatAmountEs(invoice.importe_total)}
              </span>
            </button>
          </li>
        )
      })}
    </ul>
  )
}
