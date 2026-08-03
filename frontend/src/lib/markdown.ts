const TABLE_ROW = /^\s*\|.*\|\s*$/
const DELIMITER_ROW = /^\s*\|(?:\s*:?-+:?\s*\|)+\s*$/

// GFM only recognises a table when its header row begins a new block. Both the model
// and the text extracted from filings routinely put one directly beneath a line of
// prose ("Units: dollars in millions"), which makes the parser treat every row as lazy
// continuation of that paragraph — the table renders as a wall of pipes. Inserting the
// blank line the parser expects is enough to recover it.
export function normalizeMarkdownTables(text: string): string {
  const lines = text.split("\n")
  const out: string[] = []

  for (const [i, line] of lines.entries()) {
    const startsTable = TABLE_ROW.test(line) && DELIMITER_ROW.test(lines[i + 1] ?? "")
    const previous = out[out.length - 1]
    if (startsTable && previous !== undefined && previous.trim() !== "" && !TABLE_ROW.test(previous)) {
      out.push("")
    }
    out.push(line)
  }

  return out.join("\n")
}
