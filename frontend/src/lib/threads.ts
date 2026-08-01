import { api } from "@/lib/api"

export interface Thread {
  id: string
  title: string
  created_at: string
  updated_at: string
}

export interface BackendMessage {
  id: string
  thread_id: string
  role: "user" | "assistant"
  content: string
  created_at: string
}

export const threadsApi = {
  list: () => api.get<Thread[]>("/threads"),
  create: (title: string) => api.post<Thread>("/threads", { title }),
  messages: (threadId: string) => api.get<BackendMessage[]>(`/threads/${threadId}/messages`),
}
