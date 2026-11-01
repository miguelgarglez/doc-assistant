import type { Metadata, Viewport } from "next"
import { DM_Sans, IBM_Plex_Mono, Manrope, Space_Grotesk } from "next/font/google"

import { ThemeProvider } from "@/components/theme/theme-provider"
import { PromptInputProvider } from "@/components/ai-elements/prompt-input"
import { ChatProvider } from "@/features/chat"
import { SourcesProvider } from "@/features/sources"
import { UploadsWithSources } from "@/app/uploads-with-sources"
import { AppShell } from "@/components/shell/app-shell"
import { Toaster } from "@/components/ui/sonner"
import { UploadToast } from "@/features/uploads"
import { AddSourcesProvider } from "@/features/uploads"
import { TooltipProvider } from "@/components/ui/tooltip"
import { DEFAULT_THEME, THEME_NAMES, COLOR_MODES, THEME_STORAGE_KEY, MODE_STORAGE_KEY } from "@/lib/theme"

import "./globals.css"

const industrialDisplay = Space_Grotesk({
  variable: "--font-industrial-display",
  subsets: ["latin"],
})

const industrialSans = Manrope({
  variable: "--font-industrial-sans",
  subsets: ["latin"],
})

const neutralSans = DM_Sans({
  variable: "--font-neutral-sans",
  subsets: ["latin"],
})

const plexMono = IBM_Plex_Mono({
  variable: "--font-plex-mono",
  weight: ["400", "500"],
  subsets: ["latin"],
})

export const metadata: Metadata = {
  title: "Doc Assistant",
  description:
    "Consulta local de documentación técnica de robótica industrial con citas verificables.",
}

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
  // The on-screen keyboard shrinks the layout instead of covering the composer.
  interactiveWidget: "resizes-content",
}

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="es"
      data-theme={DEFAULT_THEME}
      suppressHydrationWarning
      className={`${industrialDisplay.variable} ${industrialSans.variable} ${neutralSans.variable} ${plexMono.variable} h-dvh antialiased`}
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: `(function(){try{var t=localStorage.getItem(${JSON.stringify(THEME_STORAGE_KEY)}),m=localStorage.getItem(${JSON.stringify(MODE_STORAGE_KEY)}),r=document.documentElement;if(${JSON.stringify(THEME_NAMES)}.includes(t))r.dataset.theme=t;if(${JSON.stringify(COLOR_MODES)}.includes(m)){r.classList.toggle('dark',m==='dark');r.style.colorScheme=m}}catch(e){}})()` }} />
      </head>
      <body className="h-dvh overflow-hidden">
        <ThemeProvider>
          <TooltipProvider delay={300}>
            <SourcesProvider>
              <UploadsWithSources>
                <AddSourcesProvider>
                  <ChatProvider>
                    <PromptInputProvider>
                      <AppShell>{children}</AppShell>
                    </PromptInputProvider>
                  </ChatProvider>
                </AddSourcesProvider>
                <Toaster />
                <UploadToast />
              </UploadsWithSources>
            </SourcesProvider>
          </TooltipProvider>
        </ThemeProvider>
      </body>
    </html>
  )
}
