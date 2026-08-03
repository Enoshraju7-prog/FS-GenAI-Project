import type { CitationPayload } from "@/lib/chat-types"

interface Props {
  citations: CitationPayload[]
  onSelect: (citation: CitationPayload) => void
}

export default function CitationSources({ citations, onSelect }: Props) {
  if (citations.length === 0) return null

  return (
    <div className="mt-4 flex flex-wrap gap-2 border-t border-border pt-3">
      {citations.map((citation) => (
        <button
          key={citation.citationIndex}
          type="button"
          onClick={() => onSelect(citation)}
          className="flex items-center gap-1.5 rounded-md border border-border px-2 py-1 text-xs text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
        >
          <span className="font-medium text-foreground">[{citation.citationIndex}]</span>
          <span>
            {citation.ticker} · {citation.form} · {citation.filingDate}
          </span>
        </button>
      ))}
    </div>
  )
}
