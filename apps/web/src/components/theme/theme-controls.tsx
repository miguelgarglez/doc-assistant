"use client"

import { MoonIcon, SunIcon } from "lucide-react"

import { Button } from "@/components/ui/button"
import { useTheme } from "@/components/theme/theme-provider"
import { THEME_NAMES, modeLabel, themeLabel } from "@/lib/theme"
import { cn } from "@/lib/utils"

type ThemeControlsProps = {
  className?: string
  compact?: boolean
}

export function ThemeControls({ className, compact = false }: ThemeControlsProps) {
  const { theme, mode, setTheme, toggleMode } = useTheme()

  return (
    <div
      className={cn("flex flex-wrap items-center gap-2", className)}
      data-testid="theme-controls"
    >
      <div
        role="group"
        aria-label="Tema visual"
        className="inline-flex items-center gap-1 rounded-lg border border-border bg-card p-1"
      >
        {THEME_NAMES.map((name) => (
          <Button
            key={name}
            type="button"
            size={compact ? "xs" : "sm"}
            variant={theme === name ? "default" : "ghost"}
            aria-pressed={theme === name}
            onClick={() => setTheme(name)}
            data-testid={`theme-${name}`}
          >
            {themeLabel(name)}
          </Button>
        ))}
      </div>
      <Button
        type="button"
        size={compact ? "icon-xs" : "icon-sm"}
        variant="outline"
        onClick={toggleMode}
        aria-label={`Modo ${modeLabel(mode === "dark" ? "light" : "dark")}`}
        data-testid="mode-toggle"
      >
        {mode === "dark" ? <SunIcon /> : <MoonIcon />}
      </Button>
    </div>
  )
}
