import type { CitationPayload } from "@/lib/chat-types"

export type CitationMarkerToken =
  | { kind: "text"; text: string }
  | { kind: "citation"; citation: CitationPayload }

// Splits answer text on "[n]" markers (the grounding validator guarantees these match
// citationIndex exactly) and resolves each to its citation. A marker with no matching
// citation falls back to literal text — never throws, never drops content.
export function parseCitationMarkers(
  text: string,
  citations: CitationPayload[],
): CitationMarkerToken[] {
  const byIndex = new Map(citations.map((c) => [c.citationIndex, c]))
  const tokens: CitationMarkerToken[] = []
  const pattern = /\[(\d+)\]/g
  let lastIndex = 0
  let match: RegExpExecArray | null

  while ((match = pattern.exec(text)) !== null) {
    if (match.index > lastIndex) {
      tokens.push({ kind: "text", text: text.slice(lastIndex, match.index) })
    }

    const citation = byIndex.get(Number(match[1]))
    if (citation) {
      tokens.push({ kind: "citation", citation })
    } else {
      tokens.push({ kind: "text", text: match[0] })
    }

    lastIndex = match.index + match[0].length
  }

  if (lastIndex < text.length) {
    tokens.push({ kind: "text", text: text.slice(lastIndex) })
  }

  return tokens
}
