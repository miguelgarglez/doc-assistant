export const THEME_NAMES = ["industrial", "neutral"] as const
export type ThemeName = (typeof THEME_NAMES)[number]

export const COLOR_MODES = ["light", "dark"] as const
export type ColorMode = (typeof COLOR_MODES)[number]

export const DEFAULT_THEME: ThemeName = "industrial"
export const DEFAULT_MODE: ColorMode = "light"

export const THEME_STORAGE_KEY = "doc-assistant.theme"
export const MODE_STORAGE_KEY = "doc-assistant.mode"

export function isThemeName(value: string | null | undefined): value is ThemeName {
  return THEME_NAMES.includes(value as ThemeName)
}

export function isColorMode(value: string | null | undefined): value is ColorMode {
  return COLOR_MODES.includes(value as ColorMode)
}

export function themeLabel(theme: ThemeName): string {
  return theme === "industrial" ? "Industrial" : "Neutral"
}

export function modeLabel(mode: ColorMode): string {
  return mode === "dark" ? "Oscuro" : "Claro"
}
