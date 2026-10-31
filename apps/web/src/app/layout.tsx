import type { Metadata } from "next"
import { DM_Sans, IBM_Plex_Mono, Manrope, Space_Grotesk } from "next/font/google"

import { ThemeProvider } from "@/components/theme/theme-provider"
import { ToastProvider } from "@/components/ui/toast"
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

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="es"
      data-theme={DEFAULT_THEME}
      suppressHydrationWarning
      className={`${industrialDisplay.variable} ${industrialSans.variable} ${neutralSans.variable} ${plexMono.variable} h-full antialiased`}
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: `(function(){try{var t=localStorage.getItem(${JSON.stringify(THEME_STORAGE_KEY)}),m=localStorage.getItem(${JSON.stringify(MODE_STORAGE_KEY)}),r=document.documentElement;if(${JSON.stringify(THEME_NAMES)}.includes(t))r.dataset.theme=t;if(${JSON.stringify(COLOR_MODES)}.includes(m)){r.classList.toggle('dark',m==='dark');r.style.colorScheme=m}}catch(e){}})()` }} />
      </head>
      <body className="flex min-h-full flex-col">
        <ThemeProvider>
          <ToastProvider>{children}</ToastProvider>
        </ThemeProvider>
      </body>
    </html>
  )
}
