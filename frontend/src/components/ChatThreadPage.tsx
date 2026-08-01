import { useEffect, useRef, useState } from "react"
import { useChat } from "@ai-sdk/react"
import { DefaultChatTransport } from "ai"
import { Send } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { cn } from "@/lib/utils"
import { env } from "@/lib/env"
import { chatApi, getAccessToken, type UIMessage } from "@/lib/chat"

interface Props {
  threadId: string
}

export default function ChatThreadPage({ threadId }: Props) {
  const [initialMessages, setInitialMessages] = useState<UIMessage[]>([])
  const [ready, setReady] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    setReady(false)
    chatApi.getThread(threadId).then(({ messages }) => {
      setInitialMessages(messages)
      setReady(true)
    })
  }, [threadId])

  if (!ready) {
    return <div className="flex-1 flex items-center justify-center text-muted-foreground text-sm">Loading…</div>
  }

  return <ChatInner threadId={threadId} initialMessages={initialMessages} key={threadId} />
}

function ChatInner({ threadId, initialMessages }: { threadId: string; initialMessages: UIMessage[] }) {
  const bottomRef = useRef<HTMLDivElement>(null)

  const { messages, input, setInput, sendMessage, status } = useChat({
    transport: new DefaultChatTransport({
      url: `${env.apiBaseUrl}/chat/stream`,
      headers: async () => {
        const token = await getAccessToken()
        return token ? { Authorization: `Bearer ${token}` } : {}
      },
      body: { threadId },
    }),
    id: threadId,
    initialMessages,
  })

  const isStreaming = status === "streaming" || status === "submitted"

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!input.trim() || isStreaming) return
    await sendMessage({ text: input })
    setInput("")
  }

  return (
    <div className="flex flex-col h-screen">
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {messages.map((msg) => {
          const text = msg.parts
            .filter((p) => p.type === "text")
            .map((p) => ("text" in p ? (p as { type: string; text: string }).text : ""))
            .join("")

          return (
            <div
              key={msg.id}
              className={cn("max-w-2xl", msg.role === "user" ? "ml-auto" : "mr-auto")}
            >
              <div
                className={cn(
                  "rounded-2xl px-4 py-2.5 text-sm",
                  msg.role === "user"
                    ? "bg-primary text-primary-foreground"
                    : "bg-muted",
                )}
              >
                {text}
              </div>
            </div>
          )
        })}
        {isStreaming && (
          <div className="max-w-2xl mr-auto">
            <div className="bg-muted rounded-2xl px-4 py-2.5">
              <span className="flex gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-muted-foreground animate-bounce [animation-delay:0ms]" />
                <span className="w-1.5 h-1.5 rounded-full bg-muted-foreground animate-bounce [animation-delay:150ms]" />
                <span className="w-1.5 h-1.5 rounded-full bg-muted-foreground animate-bounce [animation-delay:300ms]" />
              </span>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <form onSubmit={handleSubmit} className="p-4 border-t flex gap-2">
        <Input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about SEC filings…"
          disabled={isStreaming}
          className="flex-1"
        />
        <Button type="submit" size="icon" disabled={!input.trim() || isStreaming}>
          <Send className="h-4 w-4" />
        </Button>
      </form>
    </div>
  )
}
