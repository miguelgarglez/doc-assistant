/** Formatea un Decimal serializado como string (p. ej. "507.49") a es-ES sin float. */
export function formatAmountEs(value: string | null | undefined): string {
  if (value == null || value === "") {
    return "—  no encontrado"
  }

  const negative = value.startsWith("-")
  const raw = negative ? value.slice(1) : value
  const [whole = "0", fraction = "00"] = raw.split(".")
  const cents = `${fraction}00`.slice(0, 2)
  const grouped = whole.replace(/\B(?=(\d{3})+(?!\d))/g, ".")
  const sign = negative ? "-" : ""
  return `${sign}${grouped},${cents} €`
}

export function displayField(value: string | null | undefined): string {
  if (value == null || value === "") {
    return "—  no encontrado"
  }
  return value
}
