/** "320 ms" under a second, "2,4 s" above. One place so every screen reads the same. */
export function duration(seconds: number): string {
  if (seconds < 1) return `${Math.round(seconds * 1000)} ms`
  return `${seconds.toFixed(seconds < 10 ? 1 : 0).replace(".", ",")} s`
}
