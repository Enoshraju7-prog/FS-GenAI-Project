import { Badge } from "@/components/ui/badge"
import type { CitationPayload } from "@/lib/chat-types"

interface Props {
  citation: CitationPayload
  onClick: (citation: CitationPayload) => void
}

export default function CitationChip({ citation, onClick }: Props) {
  return (
    <Badge
      render={<button type="button" />}
      variant="outline"
      className="mx-0.5 h-4 min-w-4 px-1 cursor-pointer align-super text-[0.65rem] leading-none hover:bg-muted"
      onClick={() => onClick(citation)}
    >
      {citation.citationIndex}
    </Badge>
  )
}
