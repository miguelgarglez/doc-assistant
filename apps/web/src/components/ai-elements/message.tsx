"use client"

import type { UIMessage } from "ai"
import { code } from "@streamdown/code"
import type { ComponentProps, HTMLAttributes } from "react"
import { memo } from "react"
import { Streamdown } from "streamdown"

import { Button } from "@/components/ui/button"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import { cn } from "@/lib/utils"

export type MessageProps = HTMLAttributes<HTMLDivElement> & {
  from: UIMessage["role"]
}

export const Message = ({ className, from, ...props }: MessageProps) => (
  <div
    className={cn(
      "group flex w-full min-w-0 flex-col gap-2",
      from === "user" ? "is-user items-end" : "is-assistant items-start",
      className
    )}
    {...props}
  />
)

export const MessageContent = ({
  children,
  className,
  ...props
}: HTMLAttributes<HTMLDivElement>) => (
  <div
    className={cn(
      "flex min-w-0 max-w-full flex-col gap-3 text-[0.9375rem] leading-7",
      "group-[.is-user]:w-fit group-[.is-user]:max-w-[85%] group-[.is-user]:rounded-2xl group-[.is-user]:rounded-br-md group-[.is-user]:bg-secondary group-[.is-user]:px-4 group-[.is-user]:py-2.5 group-[.is-user]:leading-6 group-[.is-user]:text-secondary-foreground",
      "group-[.is-assistant]:w-full group-[.is-assistant]:text-foreground",
      className
    )}
    {...props}
  >
    {children}
  </div>
)

export const MessageActions = ({
  className,
  ...props
}: ComponentProps<"div">) => (
  <div className={cn("flex items-center gap-0.5", className)} {...props} />
)

export type MessageActionProps = ComponentProps<typeof Button> & {
  label: string
}

/** Icon action with a tooltip. The accessible name is `label`. */
export const MessageAction = ({
  label,
  children,
  variant = "ghost",
  size = "icon-sm",
  className,
  ...props
}: MessageActionProps) => (
  <Tooltip>
    <TooltipTrigger
      render={
        <Button
          aria-label={label}
          className={cn("text-muted-foreground hover:text-foreground", className)}
          size={size}
          type="button"
          variant={variant}
          {...props}
        />
      }
    >
      {children}
    </TooltipTrigger>
    <TooltipContent>{label}</TooltipContent>
  </Tooltip>
)

export type MessageResponseProps = ComponentProps<typeof Streamdown>

const streamdownPlugins = { code }

export const MessageResponse = memo(
  ({ className, ...props }: MessageResponseProps) => (
    <Streamdown
      className={cn(
        "size-full [&>*:first-child]:mt-0 [&>*:last-child]:mb-0",
        className
      )}
      controls={{ code: { copy: true, download: false } }}
      plugins={streamdownPlugins}
      {...props}
    />
  ),
  (prev, next) =>
    prev.children === next.children && next.isAnimating === prev.isAnimating
)
MessageResponse.displayName = "MessageResponse"
