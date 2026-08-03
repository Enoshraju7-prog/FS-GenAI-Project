import { Fragment, cloneElement, isValidElement, type ReactElement, type ReactNode } from "react"
import ReactMarkdown, { type Components } from "react-markdown"
import remarkGfm from "remark-gfm"
import CitationChip from "@/components/CitationChip"
import type { CitationPayload } from "@/lib/chat-types"
import { parseCitationMarkers } from "@/lib/citation-markers"
import { normalizeMarkdownTables } from "@/lib/markdown"

interface Props {
  text: string
  citations?: CitationPayload[]
  onSelectCitation?: (citation: CitationPayload) => void
}

const noop = () => {}

export default function AnswerMarkdown({ text, citations = [], onSelectCitation = noop }: Props) {
  // Citation markers arrive as literal "[1]" inside the markdown, so they can only be
  // swapped for chips after parsing — walking the rendered children rather than
  // pre-splitting the source string, which would corrupt tables and lists.
  const withChips = (children: ReactNode) => replaceMarkers(children, citations, onSelectCitation)

  const components: Components = {
    p: ({ children }) => <p className="mb-3 last:mb-0 leading-relaxed">{withChips(children)}</p>,
    li: ({ children }) => <li className="mb-1">{withChips(children)}</li>,
    ul: ({ children }) => <ul className="mb-3 last:mb-0 list-disc pl-5">{children}</ul>,
    ol: ({ children }) => <ol className="mb-3 last:mb-0 list-decimal pl-5">{children}</ol>,
    h1: ({ children }) => <h2 className="mb-2 mt-4 first:mt-0 font-semibold">{withChips(children)}</h2>,
    h2: ({ children }) => <h2 className="mb-2 mt-4 first:mt-0 font-semibold">{withChips(children)}</h2>,
    h3: ({ children }) => <h3 className="mb-2 mt-4 first:mt-0 font-semibold">{withChips(children)}</h3>,
    blockquote: ({ children }) => (
      <blockquote className="mb-3 last:mb-0 border-l-2 border-border pl-3 text-muted-foreground">
        {children}
      </blockquote>
    ),
    code: ({ children }) => (
      <code className="rounded bg-muted px-1 py-0.5 text-[0.85em]">{children}</code>
    ),
    pre: ({ children }) => (
      <pre className="mb-3 last:mb-0 overflow-x-auto rounded-lg bg-muted p-3 text-xs">{children}</pre>
    ),
    // "[1](…)" is a link as far as GFM is concerned, so a citation marker that happens
    // to be followed by a parenthesis gets swallowed into an anchor — clicking it opened
    // a new tab instead of the source panel. Anything whose label is just a citation
    // index is a marker, not a link.
    a: ({ children, href }) => {
      const citation = citationForLabel(children, citations)
      if (citation) return <CitationChip citation={citation} onClick={onSelectCitation} />
      return (
        <a href={href} target="_blank" rel="noreferrer" className="underline underline-offset-2">
          {children}
        </a>
      )
    },
    // Tables are the whole reason markdown rendering exists here — financial answers
    // lean on them heavily. They scroll independently so a wide table never forces the
    // conversation column to scroll sideways.
    table: ({ children }) => (
      <div className="mb-3 last:mb-0 overflow-x-auto rounded-lg border border-border">
        <table className="w-full border-collapse text-sm">{children}</table>
      </div>
    ),
    thead: ({ children }) => <thead className="bg-muted/60">{children}</thead>,
    tr: ({ children }) => <tr className="border-b border-border last:border-0">{children}</tr>,
    th: ({ children }) => (
      <th className="px-3 py-2 text-left font-medium whitespace-nowrap">{withChips(children)}</th>
    ),
    td: ({ children }) => (
      <td className="px-3 py-2 align-top tabular-nums">{withChips(children)}</td>
    ),
  }

  return (
    <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
      {normalizeMarkdownTables(text)}
    </ReactMarkdown>
  )
}

function citationForLabel(children: ReactNode, citations: CitationPayload[]) {
  const label = typeof children === "string" ? children : Array.isArray(children) ? children.join("") : ""
  if (!/^\d+$/.test(label.trim())) return undefined
  return citations.find((c) => c.citationIndex === Number(label.trim()))
}

function replaceMarkers(
  node: ReactNode,
  citations: CitationPayload[],
  onSelectCitation: (citation: CitationPayload) => void,
): ReactNode {
  if (typeof node === "string") {
    return parseCitationMarkers(node, citations).map((token, i) =>
      token.kind === "text" ? (
        <Fragment key={i}>{token.text}</Fragment>
      ) : (
        <CitationChip key={i} citation={token.citation} onClick={onSelectCitation} />
      ),
    )
  }

  if (Array.isArray(node)) {
    return node.map((child, i) => (
      <Fragment key={i}>{replaceMarkers(child, citations, onSelectCitation)}</Fragment>
    ))
  }

  // Recurse through inline wrappers (strong, em, links) so a marker inside them still
  // becomes a chip.
  if (isValidElement(node)) {
    const element = node as ReactElement<{ children?: ReactNode }>
    if (element.props.children !== undefined) {
      return cloneElement(element, undefined, replaceMarkers(element.props.children, citations, onSelectCitation))
    }
  }

  return node
}
