import { useParams } from "react-router-dom"
import ThreadSidebar from "@/components/ThreadSidebar"
import ChatThreadPage from "@/components/ChatThreadPage"

export default function ChatLayout() {
  const { threadId } = useParams<{ threadId: string }>()

  return (
    <div className="flex h-screen overflow-hidden">
      <ThreadSidebar activeThreadId={threadId} />
      <main className="flex-1 overflow-hidden">
        {threadId ? (
          <ChatThreadPage threadId={threadId} />
        ) : (
          <EmptyState />
        )}
      </main>
    </div>
  )
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center h-full gap-3 text-center px-6">
      <h1 className="text-4xl font-bold" style={{ color: "#111" }}>Start a conversation</h1>
      <p className="max-w-sm" style={{ color: "#888" }}>
        Choose an existing thread from the sidebar or create a new chat to ask questions about SEC
        filings.
      </p>
    </div>
  )
}
