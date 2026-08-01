import { useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"
import { MessageSquarePlus } from "lucide-react"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { chatApi, type ThreadSummary } from "@/lib/chat"
import { supabase } from "@/lib/supabase"

interface Props {
  activeThreadId?: string
}

export default function ThreadSidebar({ activeThreadId }: Props) {
  const navigate = useNavigate()
  const [threads, setThreads] = useState<ThreadSummary[]>([])

  useEffect(() => {
    chatApi.listThreads().then(({ threads }) => setThreads(threads))
  }, [activeThreadId]) // re-fetch when active thread changes (title may have updated)

  async function handleNewChat() {
    const thread = await chatApi.createThread()
    navigate(`/chats/${thread.id}`)
  }

  async function handleSignOut() {
    await supabase.auth.signOut()
    navigate("/login")
  }

  return (
    <aside className="w-52 shrink-0 flex flex-col h-screen bg-white border-r border-neutral-200">
      <div className="px-4 pt-5 pb-3">
        <p className="font-semibold text-[15px] text-neutral-900">Document Copilot</p>
        <p className="text-xs text-neutral-500 mt-0.5">SEC filing assistant</p>
      </div>

      <div className="px-3 pb-3">
        <Button
          className="w-full justify-start gap-2 bg-neutral-900 hover:bg-neutral-700 text-white text-sm h-9"
          onClick={handleNewChat}
        >
          <MessageSquarePlus className="h-4 w-4" />
          New chat
        </Button>
      </div>

      <div className="flex-1 overflow-y-auto px-3 pb-3">
        <p className="text-xs text-neutral-500 mb-2">Conversations</p>
        {threads.length === 0 ? (
          <p className="text-sm text-neutral-400">No conversations yet.</p>
        ) : (
          <ul className="space-y-0.5">
            {threads.map((t) => (
              <li key={t.id}>
                <button
                  type="button"
                  onClick={() => navigate(`/chats/${t.id}`)}
                  className={cn(
                    "w-full text-left text-sm px-2 py-1.5 rounded-md hover:bg-neutral-100 truncate text-neutral-700 transition-colors",
                    activeThreadId === t.id && "bg-neutral-100 font-medium text-neutral-900",
                  )}
                >
                  {t.title}
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="px-4 py-3 border-t border-neutral-200">
        <button
          type="button"
          onClick={handleSignOut}
          className="text-sm text-neutral-500 hover:text-neutral-900 transition-colors"
        >
          Sign out
        </button>
      </div>
    </aside>
  )
}
