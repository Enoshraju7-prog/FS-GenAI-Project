import { api, getAccessToken } from "@/lib/api"
import type { AssistantUIMessage } from "@/lib/chat-types"

export interface ThreadSummary {
  id: string
  title: string
  updatedAt: string
}

export interface ThreadDetail {
  id: string
  title: string
  messages: AssistantUIMessage[]
}

export interface ChunkContextPassage {
  chunkId: string
  chunkIndex: number
  text: string
  isAnchor: boolean
}

export const chatApi = {
  listThreads: () => api.get<{ threads: ThreadSummary[] }>("/chat/threads"),
  createThread: (title = "New chat") =>
    api.post<{ id: string; title: string; createdAt: string }>("/chat/threads", { title }),
  getThread: (threadId: string) => api.get<ThreadDetail>(`/chat/threads/${threadId}`),
  deleteThread: (threadId: string) => api.delete<void>(`/chat/threads/${threadId}`),
  getChunkContext: (chunkId: string) =>
    api.get<{ passages: ChunkContextPassage[] }>(`/chat/chunks/${chunkId}/context`),
}

export { getAccessToken }
