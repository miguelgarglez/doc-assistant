import { useCallback, useState } from "react"

type Options<T> = {
  prop: T | undefined
  defaultProp: T
  onChange?: (value: T) => void
}

/** Controlled when `prop` is defined, otherwise keeps its own state. */
export function useControllableState<T>({
  prop,
  defaultProp,
  onChange,
}: Options<T>): [T, (value: T) => void] {
  const [inner, setInner] = useState(defaultProp)
  const controlled = prop !== undefined
  const value = controlled ? prop : inner
  const set = useCallback(
    (next: T) => {
      if (!controlled) setInner(next)
      onChange?.(next)
    },
    [controlled, onChange]
  )
  return [value, set]
}
