"use client"

import {
  Attachment,
  AttachmentInfo,
  AttachmentPreview,
  AttachmentRemove,
  AttachmentStatusIcon,
  Attachments,
  type AttachmentData,
} from "@/components/ai-elements/attachments"
import {
  PromptInput,
  PromptInputAttachButton,
  PromptInputBody,
  PromptInputFooter,
  PromptInputHeader,
  PromptInputSubmit,
  PromptInputTextarea,
  PromptInputTools,
  usePromptInput,
} from "@/components/ai-elements/prompt-input"
import { useConversation } from "@/features/chat/chat-provider"
import { useUploads, type UploadItem } from "@/features/uploads"

const ACCEPT = ".pdf,application/pdf,image/png,image/jpeg"

function attachmentOf(item: UploadItem): AttachmentData {
  return {
    id: item.id,
    filename: item.name,
    mediaType: item.file.type,
    url: item.previewUrl,
    status: item.status === "queued" ? "uploading" : item.status,
    progress: item.progress,
    detail: item.detail,
  }
}

export function Composer() {
  const { ask, busy, status, stop, history } = useConversation()
  const uploads = useUploads()
  const { text, setText } = usePromptInput()
  const chips = uploads.items.filter((item) => item.origin === "chat" && !item.attached)
  const uploading = chips.some((item) => item.status === "queued" || item.status === "uploading" || item.status === "processing")

  const onKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.shiftKey || event.altKey || event.metaKey || event.ctrlKey) return
    const recalled = history.cursor !== null && text === history.items[history.cursor]
    if (event.key === "ArrowUp" && (text === "" || recalled)) {
      const previous = history.peek("up")
      if (previous !== null) {
        event.preventDefault()
        setText(previous)
      }
    } else if (event.key === "ArrowDown" && recalled) {
      const next = history.peek("down")
      if (next !== null) {
        event.preventDefault()
        setText(next)
      }
    }
  }

  return (
    <PromptInput
      accept={ACCEPT}
      data-testid="composer"
      onFiles={(files) => uploads.enqueue(files, "chat")}
      onSubmit={ask}
    >
      {chips.length > 0 ? (
        <PromptInputHeader>
          <Attachments aria-label="Archivos adjuntos">
            {chips.map((item) => (
              <Attachment data={attachmentOf(item)} key={item.id} onRemove={() => uploads.dismiss(item.id)}>
                <AttachmentPreview />
                <AttachmentInfo />
                <AttachmentStatusIcon />
                <AttachmentRemove label={`Quitar ${item.name}`} />
              </Attachment>
            ))}
          </Attachments>
        </PromptInputHeader>
      ) : null}
      <PromptInputBody>
        <PromptInputTextarea onKeyDown={onKeyDown} />
      </PromptInputBody>
      <PromptInputFooter>
        <PromptInputTools>
          <PromptInputAttachButton label="Añadir PDF o factura" />
          <span className="ml-1 hidden text-xs text-muted-foreground sm:inline">
            Enter envía · Shift+Enter nueva línea
          </span>
        </PromptInputTools>
        <div className="flex items-center gap-2">
          {text.length > 900 ? (
            <span className="text-xs tabular-nums text-muted-foreground" role="status">
              {text.length}/1000
            </span>
          ) : null}
          <PromptInputSubmit disabled={!text.trim() || uploading} onStop={stop} status={busy ? status : "ready"} />
        </div>
      </PromptInputFooter>
    </PromptInput>
  )
}
