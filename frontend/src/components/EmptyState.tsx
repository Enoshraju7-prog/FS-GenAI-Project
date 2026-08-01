import { useNavigate } from "react-router-dom"
import { Button } from "@/components/ui/button"
import { threadsApi } from "@/lib/threads"

export default function EmptyState() {
  const navigate = useNavigate()

  async function handleNewChat() {
    const thread = await threadsApi.create("New chat")
    navigate(`/threads/${thread.id}`)
  }

  return (
    <div className="flex-1 flex flex-col items-center justify-center gap-4 text-center">
      <p className="text-muted-foreground">Select a conversation or start a new one.</p>
      <Button onClick={handleNewChat}>New chat</Button>
    </div>
  )
}
