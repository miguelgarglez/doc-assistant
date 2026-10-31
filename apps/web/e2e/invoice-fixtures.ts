import fs from "node:fs"
import path from "node:path"

import type {
  ErrorBody,
  Invoice,
  InvoiceUploadResponse,
} from "../src/lib/api/types"

const FIXTURES = path.join(
  process.cwd(),
  "..",
  "..",
  "evidence",
  "fixtures",
  "invoices"
)

export const FACTURA_001_PNG = fs.readFileSync(
  path.join(FIXTURES, "factura_001.png")
)

export const invoiceOkRecord = {
  numero: "F-2026-001",
  fecha_emision: "2026-01-01",
  fecha_vencimiento: "2026-12-31",
  emisor: "María Soler García",
  nif_emisor: "59516774L",
  cliente: "Talleres Puig, S.A.",
  nif_cliente: "A49117963",
  base_imponible_total: "507.49",
  cuota_iva_total: "106.57",
  irpf_tipo: "15",
  irpf_importe: "76.12",
  recargo_total: null,
  importe_total: "537.94",
  iban: null,
} as const satisfies Invoice

export const invoiceOkUpload = {
  record: invoiceOkRecord,
  estado: "ok",
  motivo: null,
  evidencias: {
    numero: "Factura F-2026-001",
    fecha_emision: "Fecha: 2026-01-01",
    fecha_vencimiento: "Vencimiento: 2026-12-31",
    emisor: "Emisor: María Soler García",
    nif_emisor: "NIF Emisor: 59516774L",
    cliente: "Cliente: Talleres Puig, S.A.",
    nif_cliente: "NIF Cliente: A49117963",
    base_imponible_total: "Subtotal 507,49",
    cuota_iva_total: "IVA 21% 106,57",
    irpf_tipo: "IRPF 15%",
    irpf_importe: "Retención IRPF 76,12",
    recargo_total: null,
    importe_total: "TOTAL 537,94",
    iban: null,
  },
  flags: {},
  fichero: "F-2026-001.png",
} as const satisfies InvoiceUploadResponse

export const invoiceReviewUpload = {
  record: {
    ...invoiceOkRecord,
    numero: "F-2026-REV",
    iban: null,
    recargo_total: null,
    cuota_iva_total: null,
  },
  estado: "revisar",
  motivo: "importes_incompletos",
  evidencias: {
    numero: "Factura F-2026-REV",
    fecha_emision: "Fecha: 2026-01-01",
    fecha_vencimiento: "Vencimiento: 2026-12-31",
    emisor: "Emisor: María Soler García",
    nif_emisor: "NIF Emisor: 59516774L",
    cliente: "Cliente: Talleres Puig, S.A.",
    nif_cliente: "NIF Cliente: A49117963",
    base_imponible_total: "Subtotal 507,49",
    cuota_iva_total: null,
    irpf_tipo: "IRPF 15%",
    irpf_importe: "Retención IRPF 76,12",
    recargo_total: null,
    importe_total: "TOTAL 537,94",
    iban: null,
  },
  flags: {
    base_imponible_total: "derivado",
  },
  fichero: "F-2026-REV.png",
} as const satisfies InvoiceUploadResponse

export const invoiceUploadError = {
  code: "invalid_file",
  message: "Only PNG/JPG invoice images are accepted",
} as const satisfies ErrorBody

export const FACTURA_001_PATH = path.join(FIXTURES, "factura_001.png")
