"use client"

import { Attachment, AttachmentInfo, AttachmentPreview, Attachments } from "@/components/ai-elements/attachments"
import { Message, MessageContent } from "@/components/ai-elements/message"
import type { AskMessage } from "@/features/chat/lib/types"
import { userText } from "@/features/chat/lib/view"

export function UserMessage({ message }: { message: AskMessage }) {
  const files = message.parts.flatMap((part, index) => (part.type === "file" ? [{ part, index }] : []))
  return (
    <Message data-testid="user-message" from="user">
      {files.length > 0 ? (
        <Attachments className="justify-end">
          {files.map(({ part, index }) => (
            <Attachment
              data={{
                id: `${message.id}-${index}`,
                filename: part.filename ?? "archivo",
                mediaType: part.mediaType,
                url: part.url.startsWith("blob:") ? part.url : undefined,
              }}
              key={`${message.id}-${index}`}
            >
              <AttachmentPreview />
              <AttachmentInfo />
            </Attachment>
          ))}
        </Attachments>
      ) : null}
      <MessageContent className="whitespace-pre-wrap">{userText(message)}</MessageContent>
    </Message>
  )
}
