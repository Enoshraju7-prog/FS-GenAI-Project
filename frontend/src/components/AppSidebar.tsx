import { useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"
import {
  SquarePen,
  ChevronsUpDown,
  LogOut,
  MessageSquare,
  MoreHorizontal,
  Trash2,
  Sun,
  Moon,
  Monitor,
} from "lucide-react"
import AppLogo from "@/components/AppLogo"
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuAction,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
} from "@/components/ui/sidebar"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import StateBanner from "@/components/StateBanner"
import { chatApi, type ThreadSummary } from "@/lib/chat"
import { supabase } from "@/lib/supabase"
import type { Theme } from "@/lib/theme"

interface Props {
  activeThreadId?: string
  theme: Theme
  onThemeChange: (theme: Theme) => void
}

export default function AppSidebar({ activeThreadId, theme, onThemeChange }: Props) {
  const navigate = useNavigate()
  const [threads, setThreads] = useState<ThreadSummary[]>([])
  const [loadError, setLoadError] = useState(false)
  const [retryCount, setRetryCount] = useState(0)
  const [email, setEmail] = useState<string | null>(null)

  useEffect(() => {
    setLoadError(false)
    chatApi
      .listThreads()
      .then(({ threads }) => setThreads(threads))
      .catch(() => setLoadError(true))
  }, [activeThreadId, retryCount]) // re-fetch when active thread changes (title may have updated) or on retry

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => setEmail(data.session?.user.email ?? null))
  }, [])

  async function handleNewChat() {
    const thread = await chatApi.createThread()
    navigate(`/chats/${thread.id}`)
  }

  async function handleDelete(threadId: string) {
    await chatApi.deleteThread(threadId)
    setThreads((current) => current.filter((t) => t.id !== threadId))
    if (activeThreadId === threadId) {
      navigate("/chats")
    }
  }

  async function handleSignOut() {
    await supabase.auth.signOut()
    navigate("/login")
  }

  const initials = email ? email.slice(0, 2).toUpperCase() : "?"
  const groups = groupByRecency(threads)

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton size="lg" tooltip="Document Copilot" onClick={() => navigate("/chats")}>
              <AppLogo />
              <div className="grid flex-1 text-left leading-tight">
                <span className="truncate font-serif text-lg">Document Copilot</span>
                <span className="truncate text-xs text-sidebar-foreground/60">SEC filing assistant</span>
              </div>
            </SidebarMenuButton>
          </SidebarMenuItem>
          <SidebarMenuItem>
            <SidebarMenuButton onClick={handleNewChat} tooltip="New chat">
              <SquarePen />
              <span>New chat</span>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>

      <SidebarContent>
        {loadError ? (
          <SidebarGroup>
            <StateBanner
              variant="error"
              title="Couldn't load conversations"
              className="py-4"
              action={{ label: "Retry", onClick: () => setRetryCount((n) => n + 1) }}
            />
          </SidebarGroup>
        ) : threads.length === 0 ? (
          <SidebarGroup>
            <StateBanner
              variant="empty"
              title="No conversations yet"
              description="Start a new chat to ask about SEC filings."
              className="py-4"
            />
          </SidebarGroup>
        ) : (
          groups.map((group) => (
            <SidebarGroup key={group.label}>
              <SidebarGroupLabel>{group.label}</SidebarGroupLabel>
              <SidebarMenu>
                {group.threads.map((t) => (
                  <SidebarMenuItem key={t.id}>
                    <SidebarMenuButton
                      isActive={activeThreadId === t.id}
                      tooltip={t.title}
                      onClick={() => navigate(`/chats/${t.id}`)}
                    >
                      {/* Collapsed mode hides the label, so without an icon the row
                          renders as a truncated letter or two. */}
                      <MessageSquare />
                      <span>{t.title}</span>
                    </SidebarMenuButton>
                    <DropdownMenu>
                      <DropdownMenuTrigger
                        render={<SidebarMenuAction showOnHover />}
                        aria-label={`Actions for ${t.title}`}
                      >
                        <MoreHorizontal />
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="start" side="right" className="w-44">
                        <DropdownMenuItem variant="destructive" onClick={() => handleDelete(t.id)}>
                          <Trash2 />
                          Delete
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </SidebarMenuItem>
                ))}
              </SidebarMenu>
            </SidebarGroup>
          ))
        )}
      </SidebarContent>

      <SidebarFooter>
        <SidebarMenu>
          <SidebarMenuItem>
            <DropdownMenu>
              <DropdownMenuTrigger render={<SidebarMenuButton size="lg" />}>
                <Avatar size="sm">
                  <AvatarFallback>{initials}</AvatarFallback>
                </Avatar>
                <div className="grid flex-1 text-left leading-tight">
                  <span className="truncate text-sm">{email ?? "Account"}</span>
                  <span className="truncate text-xs text-sidebar-foreground/60">Signed in</span>
                </div>
                <ChevronsUpDown className="ml-auto" />
              </DropdownMenuTrigger>
              <DropdownMenuContent align="start" side="top" className="w-56">
                <DropdownMenuRadioGroup
                  value={theme}
                  onValueChange={(value) => onThemeChange(value as Theme)}
                >
                  {/* DropdownMenuLabel is Base UI's Menu.GroupLabel — it reads group
                      context and throws if rendered outside a Group/RadioGroup. */}
                  <DropdownMenuLabel className="text-xs text-muted-foreground">Theme</DropdownMenuLabel>
                  <DropdownMenuRadioItem value="light">
                    <Sun />
                    Light
                  </DropdownMenuRadioItem>
                  <DropdownMenuRadioItem value="dark">
                    <Moon />
                    Dark
                  </DropdownMenuRadioItem>
                  <DropdownMenuRadioItem value="system">
                    <Monitor />
                    System
                  </DropdownMenuRadioItem>
                </DropdownMenuRadioGroup>
                <DropdownMenuSeparator />
                <DropdownMenuItem variant="destructive" onClick={handleSignOut}>
                  <LogOut />
                  Sign out
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>

      <SidebarRail />
    </Sidebar>
  )
}

function groupByRecency(threads: ThreadSummary[]) {
  const today = new Date().toDateString()
  const weekAgo = Date.now() - 7 * 24 * 60 * 60 * 1000

  const buckets: Record<string, ThreadSummary[]> = { Today: [], "Previous 7 days": [], Older: [] }
  for (const thread of threads) {
    const updated = new Date(thread.updatedAt)
    const label =
      updated.toDateString() === today ? "Today" : updated.getTime() >= weekAgo ? "Previous 7 days" : "Older"
    buckets[label].push(thread)
  }

  return Object.entries(buckets)
    .filter(([, group]) => group.length > 0)
    .map(([label, group]) => ({ label, threads: group }))
}
