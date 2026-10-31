"use client"

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react"
import { CheckIcon, XIcon } from "lucide-react"

import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

type ToastItem = {
  id: string
  message: string
  tone?: "default" | "success"
}

type ToastContextValue = {
  toast: (message: string, tone?: ToastItem["tone"]) => void
}

const ToastContext = createContext<ToastContextValue | null>(null)

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([])
  const timers = useRef(new Map<string, number>())

  const dismiss = useCallback((id: string) => {
    setItems((current) => current.filter((item) => item.id !== id))
    const timer = timers.current.get(id)
    if (timer) {
      window.clearTimeout(timer)
      timers.current.delete(id)
    }
  }, [])

  const toast = useCallback(
    (message: string, tone: ToastItem["tone"] = "default") => {
      const id = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
      setItems((current) => [...current.slice(-2), { id, message, tone }])
      const timer = window.setTimeout(() => dismiss(id), 2800)
      timers.current.set(id, timer)
    },
    [dismiss]
  )

  useEffect(() => {
    const map = timers.current
    return () => {
      for (const timer of map.values()) {
        window.clearTimeout(timer)
      }
    }
  }, [])

  return (
    <ToastContext.Provider value={{ toast }}>
      {children}
      <div
        className="pointer-events-none fixed inset-x-0 bottom-4 z-50 flex flex-col items-center gap-2 px-4"
        aria-live="polite"
        aria-relevant="additions"
        data-testid="toast-region"
      >
        {items.map((item) => (
          <div
            key={item.id}
            role="status"
            className={cn(
              "pointer-events-auto flex max-w-sm items-center gap-2 rounded-lg border border-border bg-card px-3 py-2 text-sm text-foreground shadow-[var(--shadow-panel)]",
              "motion-safe:animate-in motion-safe:fade-in motion-safe:slide-in-from-bottom-2"
            )}
            data-testid="toast"
          >
            {item.tone === "success" ? (
              <CheckIcon className="size-4 shrink-0 text-primary" aria-hidden />
            ) : null}
            <span>{item.message}</span>
            <Button
              type="button"
              size="icon-xs"
              variant="ghost"
              className="ml-1"
              aria-label="Cerrar aviso"
              onClick={() => dismiss(item.id)}
            >
              <XIcon />
            </Button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}

export function useToast() {
  const value = useContext(ToastContext)
  if (!value) {
    throw new Error("useToast debe usarse dentro de ToastProvider")
  }
  return value
}
