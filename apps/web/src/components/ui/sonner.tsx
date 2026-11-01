"use client"

import { CircleCheckIcon, InfoIcon, Loader2Icon, OctagonXIcon, TriangleAlertIcon } from "lucide-react"
import { Toaster as Sonner, type ToasterProps } from "sonner"

import { useTheme } from "@/components/theme/theme-provider"

/** shadcn Sonner on the app's own theme provider (no next-themes) and its tokens. */
const Toaster = ({ ...props }: ToasterProps) => {
  const { mode } = useTheme()

  return (
    <Sonner
      className="toaster group"
      closeButton={false}
      gap={10}
      icons={{
        success: <CircleCheckIcon className="size-4" />,
        info: <InfoIcon className="size-4" />,
        warning: <TriangleAlertIcon className="size-4" />,
        error: <OctagonXIcon className="size-4" />,
        loading: <Loader2Icon className="size-4 animate-spin motion-reduce:animate-none" />,
      }}
      position="top-right"
      offset={{ top: "max(1rem, env(safe-area-inset-top))", right: "max(1rem, env(safe-area-inset-right))" }}
      mobileOffset={{ top: "max(1rem, env(safe-area-inset-top))", right: "max(1rem, env(safe-area-inset-right))" }}
      style={
        {
          "--normal-bg": "var(--popover)",
          "--normal-text": "var(--popover-foreground)",
          "--normal-border": "var(--border)",
          "--border-radius": "var(--radius)",
          "--width": "min(26rem, calc(100vw - 2rem))",
          fontFamily: "var(--font-family-sans)",
        } as React.CSSProperties
      }
      theme={mode}
      toastOptions={{ classNames: { toast: "cn-toast shadow-[var(--shadow-panel)]" } }}
      visibleToasts={3}
      {...props}
    />
  )
}

export { Toaster }
