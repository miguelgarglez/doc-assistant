"use client"

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react"

import {
  DEFAULT_MODE,
  DEFAULT_THEME,
  MODE_STORAGE_KEY,
  THEME_STORAGE_KEY,
  isColorMode,
  isThemeName,
  type ColorMode,
  type ThemeName,
} from "@/lib/theme"

type ThemeContextValue = {
  theme: ThemeName
  mode: ColorMode
  setTheme: (theme: ThemeName) => void
  setMode: (mode: ColorMode) => void
  toggleMode: () => void
}

const ThemeContext = createContext<ThemeContextValue | null>(null)

function applyDom(theme: ThemeName, mode: ColorMode) {
  const root = document.documentElement
  root.dataset.theme = theme
  root.classList.toggle("dark", mode === "dark")
  root.style.colorScheme = mode
}

function readStoredTheme(): ThemeName {
  if (typeof window === "undefined") return DEFAULT_THEME
  let stored: string | null = null
  try { stored = window.localStorage.getItem(THEME_STORAGE_KEY) } catch {}
  return isThemeName(stored) ? stored : DEFAULT_THEME
}

function readStoredMode(): ColorMode {
  if (typeof window === "undefined") return DEFAULT_MODE
  let stored: string | null = null
  try { stored = window.localStorage.getItem(MODE_STORAGE_KEY) } catch {}
  return isColorMode(stored) ? stored : DEFAULT_MODE
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<ThemeName>(DEFAULT_THEME)
  const [mode, setModeState] = useState<ColorMode>(DEFAULT_MODE)
  const [ready, setReady] = useState(false)

  useEffect(() => {
    const nextTheme = readStoredTheme()
    const nextMode = readStoredMode()
    applyDom(nextTheme, nextMode)
    queueMicrotask(() => {
      setThemeState(nextTheme)
      setModeState(nextMode)
      setReady(true)
    })
  }, [])

  const setTheme = useCallback((next: ThemeName) => {
    try { window.localStorage.setItem(THEME_STORAGE_KEY, next) } catch {}
    setThemeState(next)
  }, [])

  const setMode = useCallback((next: ColorMode) => {
    try { window.localStorage.setItem(MODE_STORAGE_KEY, next) } catch {}
    setModeState(next)
  }, [])

  const toggleMode = useCallback(() => {
    setMode(mode === "dark" ? "light" : "dark")
  }, [mode, setMode])

  useEffect(() => {
    if (!ready) return
    applyDom(theme, mode)
  }, [theme, mode, ready])

  return (
    <ThemeContext.Provider
      value={{ theme, mode, setTheme, setMode, toggleMode }}
    >
      {children}
    </ThemeContext.Provider>
  )
}

export function useTheme() {
  const value = useContext(ThemeContext)
  if (!value) {
    throw new Error("useTheme debe usarse dentro de ThemeProvider")
  }
  return value
}
