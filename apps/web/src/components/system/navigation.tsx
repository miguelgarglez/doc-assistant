"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"

const links = [["/", "Chat"], ["/fuentes", "Fuentes"], ["/ajustes", "Ajustes"], ["/sistema", "Sistema"]] as const
export function Navigation() {
  const path = usePathname()
  const items = links.map(([href, label]) => <Link key={href} href={href} onClick={(event) => event.currentTarget.closest("details")?.removeAttribute("open")} aria-current={path === href ? "page" : undefined} className="rounded-md px-3 py-2 text-sm text-muted-foreground hover:bg-muted hover:text-foreground aria-[current=page]:bg-muted aria-[current=page]:font-medium aria-[current=page]:text-foreground">{label}</Link>)
  return <nav aria-label="Navegación principal" className="border-b border-border bg-card"><div className="mx-auto flex max-w-6xl flex-wrap items-center gap-2 px-4 py-3 sm:px-6"><Link href="/" className="mr-auto font-heading text-lg font-semibold">Doc Assistant</Link><div className="hidden items-center sm:flex">{items}</div><details className="relative sm:hidden"><summary className="cursor-pointer rounded-md border border-border px-3 py-2 text-sm">Menú</summary><div className="absolute right-0 z-20 mt-2 flex min-w-40 flex-col rounded-lg border border-border bg-card p-2 shadow-[var(--shadow-panel)]">{items}</div></details></div></nav>
}
