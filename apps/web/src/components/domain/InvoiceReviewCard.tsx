import { Badge } from "@/components/ui/badge"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"
import type { InvoiceReview } from "@/lib/domain/types"

type InvoiceReviewCardProps = {
  invoice: InvoiceReview
}

const statusLabel: Record<InvoiceReview["status"], string> = {
  pending: "Pendiente",
  approved: "Aprobada",
  flagged: "Revisar",
}

const statusVariant: Record<
  InvoiceReview["status"],
  "secondary" | "default" | "destructive"
> = {
  pending: "secondary",
  approved: "default",
  flagged: "destructive",
}

function formatMoney(amount: number, currency: string) {
  return new Intl.NumberFormat("es-ES", {
    style: "currency",
    currency,
  }).format(amount)
}

export function InvoiceReviewCard({ invoice }: InvoiceReviewCardProps) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between gap-3">
          <div className="flex flex-col gap-1">
            <CardTitle>{invoice.vendor}</CardTitle>
            <CardDescription>
              {invoice.id} · emitida {invoice.issuedOn}
            </CardDescription>
          </div>
          <Badge variant={statusVariant[invoice.status]}>
            {statusLabel[invoice.status]}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <ul className="flex flex-col gap-2">
          {invoice.lines.map((line) => (
            <li
              key={`${line.description}-${line.quantity}`}
              className="flex items-baseline justify-between gap-4 text-sm"
            >
              <span className="text-foreground">
                {line.description}
                <span className="text-muted-foreground">
                  {" "}
                  · {line.quantity} × {formatMoney(line.unitPrice, invoice.currency)}
                </span>
              </span>
              <span className="tabular-nums text-muted-foreground">
                {(line.taxRate * 100).toFixed(0)}% IVA
              </span>
            </li>
          ))}
        </ul>
        <Separator />
        <div className="flex items-baseline justify-between gap-4">
          <span className="text-sm text-muted-foreground">Total</span>
          <span className="text-sm font-medium tabular-nums">
            {formatMoney(invoice.total, invoice.currency)}
          </span>
        </div>
        {invoice.notes ? (
          <p className="text-sm text-muted-foreground">{invoice.notes}</p>
        ) : null}
      </CardContent>
    </Card>
  )
}
