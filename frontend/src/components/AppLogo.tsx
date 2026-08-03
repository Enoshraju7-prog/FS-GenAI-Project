import { cn } from "@/lib/utils"

// A soft outlined tile rather than a solid black plate: the mark already carries the
// only colour in an otherwise monochrome UI, and a black block fought with it.
export default function AppLogo({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        "flex size-8 shrink-0 items-center justify-center rounded-lg border border-border bg-background p-1",
        className,
      )}
    >
      {/* The mark is solid black on transparent, so it vanishes on a dark surface. */}
      <img src="/logo.png" alt="" className="size-full object-contain dark:invert" />
    </div>
  )
}
