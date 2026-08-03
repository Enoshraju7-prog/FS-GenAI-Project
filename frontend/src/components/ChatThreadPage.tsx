import { useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"
import { useChat } from "@ai-sdk/react"
import { DefaultChatTransport } from "ai"
import { ArrowUp } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import {
  MessageScroller,
  MessageScrollerButton,
  MessageScrollerContent,
  MessageScrollerItem,
  MessageScrollerProvider,
  MessageScrollerViewport,
} from "@/components/ui/message-scroller"
import AppLogo from "@/components/AppLogo"
import MessageBubble from "@/components/MessageBubble"
import PipelineStatus from "@/components/PipelineStatus"
import SourcePassagePanel from "@/components/SourcePassagePanel"
import StateBanner from "@/components/StateBanner"
import { env } from "@/lib/env"
import { chatApi, getAccessToken } from "@/lib/chat"
import { ApiError } from "@/lib/http"
import { isStatusPart, isTextPart, type AssistantUIMessage, type CitationPayload } from "@/lib/chat-types"

// Drawn from the client brief's example questions, so the first thing an analyst tries
// is something the corpus can actually answer.
const SUGGESTIONS = [
  "Across Apple's 2021–2025 10-Ks, how did the revenue mix between iPhone, Services, Mac, iPad, and Wearables change?",
  "For Amazon, compare AWS operating income and margin against North America and International from 2021–2025.",
  "How did NVIDIA describe demand drivers, customer concentration, and supply constraints for its Data Center business?",
  "Across Microsoft's filings, what changed in how the company describes Azure, AI infrastructure, and cloud capacity constraints?",
]

function greeting(): string {
  const hour = new Date().getHours()
  if (hour < 12) return "Good morning."
  if (hour < 18) return "Good afternoon."
  return "Good evening."
}

interface Props {
  threadId: string
  onTitleChange: (title: string) => void
}

export default function ChatThreadPage({ threadId, onTitleChange }: Props) {
  const navigate = useNavigate()
  const [initialMessages, setInitialMessages] = useState<AssistantUIMessage[]>([])
  const [loadState, setLoadState] = useState<"loading" | "ready" | "error">("loading")

  useEffect(() => {
    setLoadState("loading")
    chatApi
      .getThread(threadId)
      .then(({ messages, title }) => {
        setInitialMessages(messages)
        onTitleChange(title)
        setLoadState("ready")
      })
      .catch((err: unknown) => {
        if (err instanceof ApiError && err.status === 401) {
          navigate("/login")
          return
        }
        setLoadState("error")
      })
  }, [threadId, navigate, onTitleChange])

  if (loadState === "loading") {
    return <div className="flex-1 flex items-center justify-center text-muted-foreground text-sm">Loading…</div>
  }

  if (loadState === "error") {
    return (
      <div className="flex-1 flex items-center justify-center">
        <StateBanner
          variant="error"
          title="Couldn't load this conversation"
          description="Check your connection and try again."
          action={{ label: "Retry", onClick: () => setLoadState("loading") }}
        />
      </div>
    )
  }

  return <ChatInner threadId={threadId} initialMessages={initialMessages} key={threadId} />
}

function ChatInner({
  threadId,
  initialMessages,
}: {
  threadId: string
  initialMessages: AssistantUIMessage[]
}) {
  const [selectedCitation, setSelectedCitation] = useState<CitationPayload | null>(null)
  const [input, setInput] = useState("")

  const { messages, sendMessage, status, error, clearError } = useChat<AssistantUIMessage>({
    transport: new DefaultChatTransport({
      api: `${env.apiBaseUrl}/chat/stream`,
      headers: async (): Promise<Record<string, string>> => {
        const token = await getAccessToken()
        return token ? { Authorization: `Bearer ${token}` } : {}
      },
      body: { threadId },
      // The SDK keeps every status part on the assistant message, so replaying history
      // verbatim would resend the whole progress trail of every prior turn. It's
      // transient UI state — strip it rather than let the payload grow each turn.
      prepareSendMessagesRequest: ({ messages, body }) => ({
        body: {
          ...body,
          messages: messages.map((m) => ({ ...m, parts: m.parts.filter((p) => !isStatusPart(p)) })),
        },
      }),
    }),
    id: threadId,
    messages: initialMessages,
  })

  const isStreaming = status === "streaming" || status === "submitted"

  const lastMessage = messages[messages.length - 1]
  const lastMessageParts = lastMessage?.role === "assistant" ? lastMessage.parts : []
  const statusParts = lastMessageParts.filter(isStatusPart)
  const currentStatus = statusParts.length > 0 ? statusParts[statusParts.length - 1].data : null
  const hasAnswerText = lastMessageParts.some(isTextPart)
  const showStatus = isStreaming && !hasAnswerText

  async function send(text: string) {
    if (!text.trim() || isStreaming) return
    clearError()
    setInput("")
    await sendMessage({ text })
  }

  const composer = (
    <form
      onSubmit={(e) => {
        e.preventDefault()
        void send(input)
      }}
      className="relative w-full"
    >
      <Textarea
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault()
            void send(input)
          }
        }}
        placeholder="Ask about SEC filings…"
        rows={3}
        className="max-h-48 resize-none rounded-2xl bg-card px-4 py-3.5 pr-14 text-base shadow-sm"
      />
      <Button
        type="submit"
        size="icon"
        disabled={!input.trim() || isStreaming}
        className="absolute right-3 bottom-3 size-8 rounded-full"
      >
        <ArrowUp className="size-4" />
        <span className="sr-only">Send</span>
      </Button>
    </form>
  )

  // An empty thread is a landing page, not an empty transcript: the composer sits in
  // the middle of the canvas rather than pinned to the bottom of nothing.
  if (messages.length === 0 && !isStreaming && !error) {
    return (
      <div className="flex flex-1 min-h-0 w-full items-center justify-center overflow-y-auto px-4 py-10">
        <div className="w-full max-w-2xl">
          <div className="mb-8 flex items-center justify-center gap-3">
            <AppLogo className="size-9 rounded-lg" />
            <h1 className="font-serif text-3xl font-normal tracking-tight sm:text-4xl">{greeting()}</h1>
          </div>
          {composer}
          <div className="mt-4 grid gap-2 sm:grid-cols-2">
            {SUGGESTIONS.map((suggestion) => (
              <button
                key={suggestion}
                type="button"
                onClick={() => send(suggestion)}
                className="rounded-xl border border-border p-3 text-left text-sm text-muted-foreground transition-colors hover:bg-card hover:text-foreground"
              >
                {suggestion}
              </button>
            ))}
          </div>
          <p className="mt-6 text-center text-xs text-muted-foreground">
            Answers are grounded in SEC filings. Verify citations before relying on them.
          </p>
        </div>
        <SourcePassagePanel
          citation={selectedCitation}
          onOpenChange={(open) => !open && setSelectedCitation(null)}
        />
      </div>
    )
  }

  return (
    <div className="flex flex-1 min-h-0 w-full flex-col">
      <MessageScrollerProvider autoScroll defaultScrollPosition="last-anchor">
        <MessageScroller className="flex-1 min-h-0">
          <MessageScrollerViewport>
            <MessageScrollerContent className="mx-auto w-full max-w-2xl p-6">
              {messages.map((msg) => (
                <MessageScrollerItem key={msg.id} messageId={msg.id} scrollAnchor={msg.role === "user"}>
                  <MessageBubble message={msg} onSelectCitation={setSelectedCitation} />
                </MessageScrollerItem>
              ))}

              {showStatus && (
                <MessageScrollerItem messageId="__status">
                  <PipelineStatus status={currentStatus} />
                </MessageScrollerItem>
              )}

              {error && (
                <MessageScrollerItem messageId="__error">
                  <StateBanner variant="error" title="The assistant hit a problem" description={error.message} />
                </MessageScrollerItem>
              )}
            </MessageScrollerContent>
          </MessageScrollerViewport>
          <MessageScrollerButton />
        </MessageScroller>
      </MessageScrollerProvider>

      <div className="px-4 pb-3">
        <div className="mx-auto w-full max-w-2xl">{composer}</div>
        <p className="mt-2 text-center text-xs text-muted-foreground">
          Answers are grounded in SEC filings. Verify citations before relying on them.
        </p>
      </div>

      <SourcePassagePanel
        citation={selectedCitation}
        onOpenChange={(open) => !open && setSelectedCitation(null)}
      />
    </div>
  )
}
