import type { UIMessage } from "ai"

// Payload shapes mirroring backend/app/schemas/chat.py's CitationPayload/StatusPayload,
// field-for-field, as they arrive over the wire (camelCase, matching the backend's
// _CamelModel aliasing).

export interface CitationPayload {
  citationIndex: number
  chunkId: string
  excerpt: string
  ticker: string
  companyName: string | null
  form: string
  filingDate: string
  page: string | null
  section: string | null
}

export interface StatusPayload {
  stage: string
  message: string
}

// Registers our two data-part kinds with the AI SDK's generic UIMessage so the SDK
// produces exactly the wire shape the backend emits: {"type":"data-citation","data":{...}}
// and {"type":"data-status","data":{...}}.
export type ChatDataParts = {
  citation: CitationPayload
  status: StatusPayload
}

export type AssistantUIMessage = UIMessage<unknown, ChatDataParts>
export type AssistantUIMessagePart = AssistantUIMessage["parts"][number]

export type TextPart = Extract<AssistantUIMessagePart, { type: "text" }>
export type CitationPart = Extract<AssistantUIMessagePart, { type: "data-citation" }>
export type StatusPart = Extract<AssistantUIMessagePart, { type: "data-status" }>

export function isTextPart(part: AssistantUIMessagePart): part is TextPart {
  return part.type === "text"
}

export function isCitationPart(part: AssistantUIMessagePart): part is CitationPart {
  return part.type === "data-citation"
}

export function isStatusPart(part: AssistantUIMessagePart): part is StatusPart {
  return part.type === "data-status"
}
