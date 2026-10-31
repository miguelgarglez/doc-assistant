"use client"

import { useState } from "react"
import { ZoomInIcon, ZoomOutIcon } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"
import { invoiceImageUrl } from "@/lib/api/source-url"
import type { Invoice, InvoiceUploadResponse } from "@/lib/api/types"
import { displayField, formatAmountEs } from "@/lib/domain/format-amount"
import { cn } from "@/lib/utils"

type FieldDef = {
  key: keyof Invoice
  label: string
  kind: "text" | "amount"
}

const FIELDS: readonly FieldDef[] = [
  { key: "numero", label: "Número", kind: "text" },
  { key: "fecha_emision", label: "Fecha emisión", kind: "text" },
  { key: "fecha_vencimiento", label: "Fecha vencimiento", kind: "text" },
  { key: "emisor", label: "Emisor", kind: "text" },
  { key: "nif_emisor", label: "NIF emisor", kind: "text" },
  { key: "cliente", label: "Cliente", kind: "text" },
  { key: "nif_cliente", label: "NIF cliente", kind: "text" },
  { key: "base_imponible_total", label: "Base imponible", kind: "amount" },
  { key: "cuota_iva_total", label: "IVA", kind: "amount" },
  { key: "irpf_tipo", label: "IRPF tipo", kind: "text" },
  { key: "irpf_importe", label: "IRPF importe", kind: "amount" },
  { key: "recargo_total", label: "Recargo", kind: "amount" },
  { key: "importe_total", label: "Total", kind: "amount" },
  { key: "iban", label: "IBAN", kind: "text" },
]

type InvoiceReviewCardProps = {
  data: InvoiceUploadResponse
}

function formatIrpfTipo(value: string | null | undefined): string {
  if (value == null || value === "") {
    return "—  no encontrado"
  }
  return `${value.replace(".", ",")}%`
}

function fieldValue(key: keyof Invoice, record: Invoice): string {
  const raw = record[key]
  if (key === "irpf_tipo") {
    return formatIrpfTipo(raw)
  }
  const def = FIELDS.find((field) => field.key === key)
  if (def?.kind === "amount") {
    return formatAmountEs(raw)
  }
  return displayField(raw)
}

export function InvoiceReviewCard({ data }: InvoiceReviewCardProps) {
  const { record, estado, motivo, evidencias, flags = {} } = data
  const imageSrc = invoiceImageUrl(record.numero)
  const [zoomed, setZoomed] = useState(false)
  const isOk = estado === "ok"
  const isReview = estado === "revisar"

  return (
    <Card data-testid="invoice-review-card">
      <CardHeader className="gap-3">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="flex min-w-0 flex-col gap-1">
            <CardTitle className="font-mono text-base">
              {displayField(record.numero)}
            </CardTitle>
            <CardDescription>
              {displayField(record.emisor)}
              {record.fecha_emision
                ? ` · emitida ${record.fecha_emision}`
                : null}
            </CardDescription>
          </div>
          {estado ? (
            <Badge
              variant={isReview ? "destructive" : isOk ? "default" : "secondary"}
              data-testid="invoice-estado"
              className={
                isOk
                  ? "border-transparent bg-[color:var(--ok-bg)] text-[color:var(--ok-fg)]"
                  : isReview
                    ? "border-transparent bg-[color:var(--review-bg)] text-[color:var(--review-fg)]"
                    : undefined
              }
            >
              {estado}
            </Badge>
          ) : (
            <Badge variant="secondary" data-testid="invoice-estado">
              indexada
            </Badge>
          )}
        </div>
        {motivo ? (
          <p
            className="rounded-md border border-border bg-muted/50 px-3 py-2 text-sm text-foreground"
            data-testid="invoice-motivo"
            role="status"
          >
            Motivo: {motivo}
          </p>
        ) : null}
      </CardHeader>
      <CardContent className="flex flex-col gap-6">
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <ul className="flex flex-col gap-2" data-testid="invoice-fields">
            {FIELDS.map((field) => {
              const value = fieldValue(field.key, record)
              const evidence = evidencias[field.key]
              const flag = flags[field.key]
              const missing = value === "—  no encontrado"

              return (
                <li
                  key={field.key}
                  className="rounded-md border border-transparent px-1 py-1.5 hover:border-border hover:bg-muted/40"
                  data-field={field.key}
                >
                  <div className="flex items-baseline justify-between gap-3 text-sm">
                    <span className="shrink-0 text-muted-foreground">
                      {field.label}
                      {flag === "derivado" ? (
                        <Badge
                          variant="outline"
                          className="ml-2 align-middle"
                          data-testid={`flag-derivado-${field.key}`}
                        >
                          derivado
                        </Badge>
                      ) : null}
                    </span>
                    <span
                      className={cn(
                        "text-right tabular-nums",
                        missing
                          ? "text-muted-foreground"
                          : "font-medium text-foreground",
                        field.key === "importe_total" && !missing
                          ? "text-base"
                          : null
                      )}
                    >
                      {value}
                    </span>
                  </div>
                  {evidence ? (
                    <details className="mt-1 group">
                      <summary className="cursor-pointer text-xs text-muted-foreground outline-none focus-visible:ring-3 focus-visible:ring-ring/50">
                        Evidencia OCR
                      </summary>
                      <p className="mt-1 rounded-md bg-muted/60 px-2 py-1.5 font-mono text-xs leading-relaxed text-foreground">
                        {evidence}
                      </p>
                    </details>
                  ) : null}
                </li>
              )
            })}
          </ul>

          <div className="flex flex-col gap-2">
            <p className="text-xs font-medium text-muted-foreground">
              Imagen de la factura
            </p>
            <button
              type="button"
              onClick={() => setZoomed((current) => !current)}
              className="group relative overflow-hidden rounded-md border border-border bg-muted text-left outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
              aria-pressed={zoomed}
              aria-label={
                zoomed
                  ? "Reducir imagen de factura"
                  : "Ampliar imagen de factura"
              }
              data-testid="invoice-image-zoom"
            >
              {/* eslint-disable-next-line @next/next/no-img-element -- PNG/JPG dinámico del proxy BFF */}
              <img
                src={imageSrc}
                alt={`Factura ${record.numero}`}
                width={480}
                height={640}
                className={
                  zoomed
                    ? "h-auto w-full object-contain object-top"
                    : "mx-auto h-auto max-h-80 w-full object-contain object-top"
                }
              />
              <span className="pointer-events-none absolute right-2 bottom-2 inline-flex items-center gap-1 rounded-md border border-border bg-card/90 px-2 py-1 text-xs text-muted-foreground">
                {zoomed ? (
                  <ZoomOutIcon className="size-3.5" />
                ) : (
                  <ZoomInIcon className="size-3.5" />
                )}
                {zoomed ? "Clic para reducir" : "Clic para ampliar"}
              </span>
            </button>
          </div>
        </div>
        <Separator />
        <p className="text-xs text-muted-foreground">
          Los importes se muestran tal cual del servicio (Decimal como texto).
          Los valores ausentes nunca se inventan.
        </p>
      </CardContent>
    </Card>
  )
}
