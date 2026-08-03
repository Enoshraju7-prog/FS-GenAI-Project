import { useEffect, useState } from "react"
import { useParams } from "react-router-dom"
import { Moon, Sun } from "lucide-react"
import AppSidebar from "@/components/AppSidebar"
import ChatThreadPage from "@/components/ChatThreadPage"
import StateBanner from "@/components/StateBanner"
import { Button } from "@/components/ui/button"
import { SidebarInset, SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar"
import { applyTheme, getStoredTheme, prefersDark, setStoredTheme, watchSystemTheme, type Theme } from "@/lib/theme"

export default function ChatLayout() {
  const { threadId } = useParams<{ threadId: string }>()
  const [threadTitle, setThreadTitle] = useState("")

  // Theme lives here so the header toggle and the sidebar menu can't drift apart.
  const [theme, setTheme] = useState<Theme>(getStoredTheme)

  useEffect(() => {
    if (theme !== "system") return
    return watchSystemTheme(() => applyTheme("system"))
  }, [theme])

  useEffect(() => setThreadTitle(""), [threadId])

  function changeTheme(next: Theme) {
    setTheme(next)
    setStoredTheme(next)
  }

  const isDark = theme === "dark" || (theme === "system" && prefersDark())

  return (
    // h-svh (not the primitive's default min-h-svh) so the shell is exactly the
    // viewport and the message list scrolls inside it instead of growing the page.
    <SidebarProvider className="h-svh overflow-hidden">
      <AppSidebar activeThreadId={threadId} theme={theme} onThemeChange={changeTheme} />
      <SidebarInset className="min-h-0 overflow-hidden">
        <div className="flex items-center gap-2 border-b px-3 py-2">
          <SidebarTrigger />
          <p className="flex-1 truncate text-sm font-medium text-foreground">{threadTitle}</p>
          <Button
            variant="ghost"
            size="icon"
            className="size-8"
            onClick={() => changeTheme(isDark ? "light" : "dark")}
            aria-label={isDark ? "Switch to light mode" : "Switch to dark mode"}
          >
            {isDark ? <Sun className="size-4" /> : <Moon className="size-4" />}
          </Button>
        </div>
        {/* The chat fills the remaining height and scrolls internally; only the empty
            state is centred. Centring the chat too stops it stretching, so a long
            answer overflows the viewport with nothing able to scroll. */}
        {threadId ? (
          <ChatThreadPage threadId={threadId} onTitleChange={setThreadTitle} />
        ) : (
          <div className="flex flex-1 min-h-0 items-center justify-center">
            <StateBanner
              variant="empty"
              title="Start a conversation"
              description="Choose an existing thread from the sidebar or create a new chat to ask questions about SEC filings."
            />
          </div>
        )}
      </SidebarInset>
    </SidebarProvider>
  )
}
