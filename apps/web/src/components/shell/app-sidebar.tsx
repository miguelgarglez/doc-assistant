"use client"

import {
  ActivityIcon,
  FileSearchIcon,
  LibraryIcon,
  PlusIcon,
  MessageSquareIcon,
  SettingsIcon,
  SquarePenIcon,
} from "lucide-react"
import Link from "next/link"
import { usePathname, useRouter } from "next/navigation"

import { HistoryPanel } from "@/components/history/history-panel"
import { useAddSources } from "@/components/providers/add-sources-provider"
import { useConversation } from "@/components/providers/chat-provider"
import { useSources } from "@/components/providers/sources-provider"
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  useSidebar,
} from "@/components/ui/sidebar"

export const NAV_ITEMS = [
  { href: "/", label: "Chat", icon: MessageSquareIcon },
  { href: "/fuentes", label: "Fuentes", icon: LibraryIcon },
  { href: "/sistema", label: "Sistema", icon: ActivityIcon },
  { href: "/ajustes", label: "Ajustes", icon: SettingsIcon },
] as const

export function AppSidebar() {
  const pathname = usePathname()
  const router = useRouter()
  const { setOpenMobile } = useSidebar()
  const { messages, clear } = useConversation()
  const sources = useSources()
  const addSources = useAddSources()

  const newConversation = () => {
    clear()
    setOpenMobile(false)
    router.push("/")
  }

  return (
    <Sidebar aria-label="Navegación principal" collapsible="offcanvas">
      <SidebarHeader className="gap-3 p-3">
        <Link
          className="flex items-center gap-2 rounded-md px-1 py-1 outline-none focus-visible:ring-2 focus-visible:ring-sidebar-ring"
          href="/"
          onClick={() => setOpenMobile(false)}
        >
          <span className="flex size-7 items-center justify-center rounded-md bg-sidebar-primary text-sidebar-primary-foreground">
            <FileSearchIcon className="size-4" />
          </span>
          <span className="font-heading text-[0.9375rem] font-semibold tracking-tight">Doc Assistant</span>
        </Link>
        <button
          className="flex h-8 w-full cursor-pointer items-center gap-2 rounded-md border border-sidebar-border bg-background px-2.5 text-sm font-medium transition-[background-color,transform] duration-150 ease-[var(--ease-out)] outline-none hover:bg-sidebar-accent focus-visible:ring-2 focus-visible:ring-sidebar-ring active:scale-[0.97] disabled:cursor-default disabled:opacity-50 disabled:active:scale-100"
          data-testid="new-conversation"
          disabled={messages.length === 0}
          onClick={newConversation}
          type="button"
        >
          <SquarePenIcon className="size-4" />
          Nueva conversación
        </button>
        <button
          className="flex h-9 w-full cursor-pointer items-center justify-center gap-2 rounded-md bg-sidebar-primary px-2.5 text-sm font-medium text-sidebar-primary-foreground transition-[background-color,transform] duration-150 ease-[var(--ease-out)] outline-none focus-visible:ring-2 focus-visible:ring-sidebar-ring active:scale-[0.97] motion-reduce:active:scale-100 [@media(hover:hover)]:hover:bg-sidebar-primary/90"
          data-testid="add-sources"
          onClick={() => {
            setOpenMobile(false)
            addSources.setOpen(true)
          }}
          type="button"
        >
          <PlusIcon className="size-4" />
          Añadir fuentes
        </button>
      </SidebarHeader>
      <SidebarContent>
        <SidebarGroup className="py-0">
          <SidebarGroupContent>
            <SidebarMenu>
              <SidebarMenuItem><HistoryPanel /></SidebarMenuItem>
              {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
                const active = href === "/" ? pathname === "/" : pathname.startsWith(href)
                return (
                  <SidebarMenuItem key={href}>
                    <SidebarMenuButton
                      isActive={active}
                      render={
                        <Link
                          aria-current={active ? "page" : undefined}
                          href={href}
                          onClick={() => setOpenMobile(false)}
                        />
                      }
                    >
                      <Icon />
                      <span>{label}</span>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                )
              })}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
      <SidebarFooter className="p-3">
        <p className="px-1 text-xs text-muted-foreground" data-testid="sidebar-sources-count">
          {sources.status === "loading"
            ? "Cargando fuentes…"
            : sources.items.length === 0
              ? "Sin fuentes indexadas"
              : sources.items.length === 1
                ? "1 fuente indexada"
                : `${sources.items.length} fuentes indexadas`}
        </p>
      </SidebarFooter>
    </Sidebar>
  )
}
