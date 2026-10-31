"use client"

import type { ReactNode } from "react"

import { PromptInputProvider } from "@/components/ai-elements/prompt-input"
import { ChatProvider } from "@/components/providers/chat-provider"
import { SourcesProvider } from "@/components/providers/sources-provider"
import { UploadsProvider } from "@/components/providers/uploads-provider"
import { ThemeProvider } from "@/components/theme/theme-provider"
import { ToastProvider } from "@/components/ui/toast"
import { TooltipProvider } from "@/components/ui/tooltip"

/** Order matters: uploads refresh the sources, and chat reads the uploads it attaches. */
export function AppProviders({ children }: { children: ReactNode }) {
  return (
    <ThemeProvider>
      <ToastProvider>
        <TooltipProvider delay={400} closeDelay={0}>
          <SourcesProvider>
            <UploadsProvider>
              <ChatProvider>
                <PromptInputProvider>{children}</PromptInputProvider>
              </ChatProvider>
            </UploadsProvider>
          </SourcesProvider>
        </TooltipProvider>
      </ToastProvider>
    </ThemeProvider>
  )
}
