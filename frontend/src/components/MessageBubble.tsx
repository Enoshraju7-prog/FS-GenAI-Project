import { Message, MessageContent } from "@/components/ui/message"
import { Bubble, BubbleContent } from "@/components/ui/bubble"
import AnswerMarkdown from "@/components/AnswerMarkdown"
import CitationSources from "@/components/CitationSources"
import { isCitationPart, isTextPart } from "@/lib/chat-types"
import type { AssistantUIMessage, CitationPayload } from "@/lib/chat-types"

interface Props {
  message: AssistantUIMessage
  onSelectCitation: (citation: CitationPayload) => void
}

export default function MessageBubble({ message, onSelectCitation }: Props) {
  const text = message.parts.filter(isTextPart).map((p) => p.text).join("")
  const isUser = message.role === "user"

  if (isUser) {
    return (
      <Message align="end">
        <MessageContent>
          <Bubble variant="secondary">
            <BubbleContent>{text}</BubbleContent>
          </Bubble>
        </MessageContent>
      </Message>
    )
  }

  // The model can cite the same source in several places; the footer lists each source
  // once, while the inline chips still mark every spot it was used.
  const citations = dedupeByIndex(message.parts.filter(isCitationPart).map((p) => p.data))

  return (
    <Message align="start">
      <MessageContent>
        <Bubble variant="ghost">
          <BubbleContent>
            <AnswerMarkdown text={text} citations={citations} onSelectCitation={onSelectCitation} />
            <CitationSources citations={citations} onSelect={onSelectCitation} />
          </BubbleContent>
        </Bubble>
      </MessageContent>
    </Message>
  )
}

function dedupeByIndex(citations: CitationPayload[]): CitationPayload[] {
  return [...new Map(citations.map((c) => [c.citationIndex, c])).values()].sort(
    (a, b) => a.citationIndex - b.citationIndex,
  )
}
