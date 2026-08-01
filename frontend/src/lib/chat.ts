import { api, getAccessToken } from "@/lib/api"

export interface ThreadSummary {
  id: string
  title: string
  updatedAt: string
}

export interface UIMessagePart {
  type: string
  text: string
}

export interface UIMessage {
  id: string
  role: "user" | "assistant"
  parts: UIMessagePart[]
}

export interface ThreadDetail {
  id: string
  title: string
  messages: UIMessage[]
}

export const chatApi = {
  listThreads: () => api.get<{ threads: ThreadSummary[] }>("/chat/threads"),
  createThread: (title = "New chat") =>
    api.post<{ id: string; title: string; createdAt: string }>("/chat/threads", { title }),
  getThread: (threadId: string) => api.get<ThreadDetail>(`/chat/threads/${threadId}`),
}

export { getAccessToken }
