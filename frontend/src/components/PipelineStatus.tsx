import type { StatusPayload } from "@/lib/chat-types"

interface Props {
  status: StatusPayload | null
}

// A single line that gets replaced as the run advances, rather than a trail or a
// breadcrumb of every stage. The gradient wipe carries the "still working" signal, so
// there's no spinner or dots alongside it.
export default function PipelineStatus({ status }: Props) {
  return (
    <p role="status" aria-live="polite" className="text-shimmer text-sm">
      {status?.message ?? "Thinking…"}
    </p>
  )
}
