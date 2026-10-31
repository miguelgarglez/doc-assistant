"use client"

import { ArrowUpIcon, PaperclipIcon, SquareIcon } from "lucide-react"
import type {
  ChangeEvent,
  ComponentProps,
  FormEvent,
  HTMLAttributes,
  KeyboardEvent,
  ReactNode,
  RefObject,
} from "react"
import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState,
} from "react"

import {
  InputGroup,
  InputGroupAddon,
  InputGroupButton,
  InputGroupTextarea,
} from "@/components/ui/input-group"
import { Spinner } from "@/components/ui/spinner"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import { cn } from "@/lib/utils"

type PromptInputController = {
  text: string
  setText: (value: string) => void
  textareaRef: RefObject<HTMLTextAreaElement | null>
  openFileDialog: () => void
  registerFileInput: (open: () => void) => void
}

const Controller = createContext<PromptInputController | null>(null)

export const usePromptInput = () => {
  const ctx = useContext(Controller)
  if (!ctx) throw new Error("usePromptInput needs a PromptInputProvider")
  return ctx
}

/** Lifts the draft text out of the form so suggestions, history and shortcuts can set it. */
export const PromptInputProvider = ({ children }: { children: ReactNode }) => {
  const [text, setText] = useState("")
  const textareaRef = useRef<HTMLTextAreaElement | null>(null)
  const openRef = useRef<() => void>(() => undefined)
  const registerFileInput = useCallback((open: () => void) => {
    openRef.current = open
  }, [])
  const openFileDialog = useCallback(() => openRef.current(), [])
  const value = useMemo(
    () => ({ text, setText, textareaRef, openFileDialog, registerFileInput }),
    [text, openFileDialog, registerFileInput]
  )
  return <Controller.Provider value={value}>{children}</Controller.Provider>
}

export type PromptInputProps = Omit<HTMLAttributes<HTMLFormElement>, "onSubmit"> & {
  accept?: string
  onSubmit: (text: string) => void
  onFiles: (files: File[]) => void
}

/** The form owns the hidden file input. Paste and drop are handled by the textarea and the page-level drop zone. */
export const PromptInput = ({
  className,
  accept,
  onSubmit,
  onFiles,
  children,
  ...props
}: PromptInputProps) => {
  const { text, setText, registerFileInput } = usePromptInput()
  const inputRef = useRef<HTMLInputElement | null>(null)
  const bindInput = useCallback(
    (node: HTMLInputElement | null) => {
      inputRef.current = node
      registerFileInput(() => node?.click())
    },
    [registerFileInput]
  )

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const value = text.trim()
    if (!value) return
    setText("")
    onSubmit(value)
  }

  const handleChange = (event: ChangeEvent<HTMLInputElement>) => {
    const picked = Array.from(event.currentTarget.files ?? [])
    event.currentTarget.value = ""
    if (picked.length > 0) onFiles(picked)
  }

  return (
    <PromptInputFilesContext.Provider value={onFiles}>
      <input
        accept={accept}
        aria-label="Añadir fuentes"
        className="hidden"
        multiple
        onChange={handleChange}
        ref={bindInput}
        tabIndex={-1}
        type="file"
      />
      <form className={cn("w-full", className)} onSubmit={handleSubmit} {...props}>
        <InputGroup className="overflow-hidden rounded-2xl border-border bg-card shadow-sm transition-shadow duration-150 focus-within:shadow-md dark:bg-card">
          {children}
        </InputGroup>
      </form>
    </PromptInputFilesContext.Provider>
  )
}

const PromptInputFilesContext = createContext<(files: File[]) => void>(() => undefined)

export const PromptInputBody = ({ className, ...props }: HTMLAttributes<HTMLDivElement>) => (
  <div className={cn("contents", className)} {...props} />
)

export const PromptInputHeader = ({
  className,
  ...props
}: Omit<ComponentProps<typeof InputGroupAddon>, "align">) => (
  <InputGroupAddon align="block-start" className={cn("flex-wrap gap-1.5", className)} {...props} />
)

export const PromptInputFooter = ({
  className,
  ...props
}: Omit<ComponentProps<typeof InputGroupAddon>, "align">) => (
  <InputGroupAddon align="block-end" className={cn("justify-between gap-1", className)} {...props} />
)

export const PromptInputTools = ({ className, ...props }: HTMLAttributes<HTMLDivElement>) => (
  <div className={cn("flex min-w-0 items-center gap-1", className)} {...props} />
)

export const PromptInputTextarea = ({
  onKeyDown,
  className,
  placeholder = "Pregunta sobre tus fuentes",
  ...props
}: Omit<ComponentProps<typeof InputGroupTextarea>, "value" | "onChange">) => {
  const { text, setText, textareaRef } = usePromptInput()
  const onFiles = useContext(PromptInputFilesContext)
  const [composing, setComposing] = useState(false)

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    // keyCode 229 covers Safari, which ends the composition before the Enter keydown fires.
    if (composing || event.nativeEvent.isComposing || event.nativeEvent.keyCode === 229) return
    onKeyDown?.(event)
    if (event.defaultPrevented) return
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault()
      const { form } = event.currentTarget
      const submit = form?.querySelector<HTMLButtonElement>('button[type="submit"]')
      if (submit && !submit.disabled) form?.requestSubmit()
    }
  }

  return (
    <InputGroupTextarea
      aria-label="Pregunta"
      className={cn("field-sizing-content max-h-48 min-h-11 px-4 py-3 text-[0.9375rem] leading-6", className)}
      maxLength={1000}
      name="message"
      onChange={(event) => setText(event.currentTarget.value)}
      onCompositionEnd={() => setComposing(false)}
      onCompositionStart={() => setComposing(true)}
      onKeyDown={handleKeyDown}
      onPaste={(event) => {
        const files = Array.from(event.clipboardData.files)
        if (files.length === 0) return
        event.preventDefault()
        onFiles(files)
      }}
      placeholder={placeholder}
      ref={textareaRef}
      rows={1}
      value={text}
      {...props}
    />
  )
}

export const PromptInputButton = ({
  tooltip,
  className,
  ...props
}: ComponentProps<typeof InputGroupButton> & { tooltip?: string }) => {
  const button = (
    <InputGroupButton className={cn("text-muted-foreground hover:text-foreground", className)} {...props} />
  )
  if (!tooltip) return button
  return (
    <Tooltip>
      <TooltipTrigger render={button} />
      <TooltipContent>{tooltip}</TooltipContent>
    </Tooltip>
  )
}

export const PromptInputAttachButton = ({ label = "Añadir fuente" }: { label?: string }) => {
  const { openFileDialog } = usePromptInput()
  return (
    <PromptInputButton aria-label={label} onClick={openFileDialog} size="icon-sm" tooltip={label}>
      <PaperclipIcon />
    </PromptInputButton>
  )
}

export type PromptInputStatus = "ready" | "submitted" | "streaming" | "error"

/** Send when idle, stop while a response is in flight. */
export const PromptInputSubmit = ({
  status = "ready",
  onStop,
  disabled,
  className,
  ...props
}: Omit<ComponentProps<typeof InputGroupButton>, "type"> & {
  status?: PromptInputStatus
  onStop?: () => void
}) => {
  const busy = status === "submitted" || status === "streaming"
  const label = busy ? "Detener" : "Enviar pregunta"
  return (
    <Tooltip>
      <TooltipTrigger
        render={
          <InputGroupButton
            aria-label={label}
            className={cn("rounded-full", className)}
            data-testid={busy ? "cancel-ask" : "send-ask"}
            disabled={busy ? false : disabled}
            onClick={busy ? onStop : undefined}
            size="icon-sm"
            type={busy ? "button" : "submit"}
            variant="default"
            {...props}
          />
        }
      >
        {status === "submitted" ? <Spinner /> : busy ? <SquareIcon className="fill-current" /> : <ArrowUpIcon />}
      </TooltipTrigger>
      <TooltipContent>{label}</TooltipContent>
    </Tooltip>
  )
}
