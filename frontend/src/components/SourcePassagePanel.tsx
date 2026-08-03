import { useEffect, useState } from "react"
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { Badge } from "@/components/ui/badge"
import AnswerMarkdown from "@/components/AnswerMarkdown"
import { chatApi, type ChunkContextPassage } from "@/lib/chat"
import type { CitationPayload } from "@/lib/chat-types"

interface Props {
  citation: CitationPayload | null
  onOpenChange: (open: boolean) => void
}

export default function SourcePassagePanel({ citation, onOpenChange }: Props) {
  return (
    <Sheet open={citation !== null} onOpenChange={onOpenChange}>
      <SheetContent className="sm:max-w-lg overflow-y-auto">
        {citation && <PanelBody citation={citation} />}
      </SheetContent>
    </Sheet>
  )
}

function PanelBody({ citation }: { citation: CitationPayload }) {
  const [passages, setPassages] = useState<ChunkContextPassage[] | null>(null)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    setPassages(null)
    setFailed(false)
    chatApi
      .getChunkContext(citation.chunkId)
      .then(({ passages }) => setPassages(passages))
      .catch(() => setFailed(true))
  }, [citation.chunkId])

  return (
    <>
      <SheetHeader>
        <SheetTitle className="flex items-center gap-2">
          <span className="flex size-6 shrink-0 items-center justify-center rounded-md bg-foreground text-xs font-medium text-background">
            {citation.citationIndex}
          </span>
          {citation.companyName ?? citation.ticker}
        </SheetTitle>
        <div className="flex flex-wrap gap-1.5 pt-1">
          <Badge variant="outline">{citation.ticker}</Badge>
          <Badge variant="outline">{citation.form}</Badge>
          <Badge variant="outline">Filed {citation.filingDate}</Badge>
          {citation.section && <Badge variant="outline">{citation.section}</Badge>}
        </div>
      </SheetHeader>

      <div className="space-y-3 px-4 pb-6">
        <div>
          <p className="text-xs font-medium tracking-wide text-muted-foreground uppercase">Source context</p>
          <p className="mt-1 text-xs text-muted-foreground">
            Neighboring chunks are shown around the cited passage for continuity.
          </p>
        </div>

        {passages === null && !failed && (
          <div className="rounded-xl border border-border p-4 text-sm text-muted-foreground">
            Loading source context…
          </div>
        )}

        {failed && (
          // Falling back to the citation's own excerpt keeps the panel useful even if
          // the context lookup fails.
          <PassageCard label="Cited passage" anchor text={citation.excerpt} />
        )}

        {passages?.map((passage, i) => (
          <PassageCard
            key={passage.chunkId}
            label={passage.isAnchor ? "Cited passage" : i < anchorIndex(passages) ? "Previous context" : "Next context"}
            anchor={passage.isAnchor}
            chunkLabel={`Chunk ${passage.chunkIndex}`}
            text={passage.text}
          />
        ))}
      </div>
    </>
  )
}

function anchorIndex(passages: ChunkContextPassage[]) {
  return passages.findIndex((p) => p.isAnchor)
}

function PassageCard({
  label,
  anchor,
  chunkLabel,
  text,
}: {
  label: string
  anchor: boolean
  chunkLabel?: string
  text: string
}) {
  return (
    <div className={anchor ? "rounded-xl border-2 border-foreground/20 p-3" : "rounded-xl border border-border p-3"}>
      <div className="mb-2 flex items-center gap-2">
        <Badge variant={anchor ? "default" : "secondary"} className="text-[0.65rem] tracking-wide uppercase">
          {label}
        </Badge>
        {chunkLabel && <span className="text-xs text-muted-foreground">{chunkLabel}</span>}
      </div>
      <div className="text-sm text-foreground">
        <AnswerMarkdown text={text} />
      </div>
    </div>
  )
}
