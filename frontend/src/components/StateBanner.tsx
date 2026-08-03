import { AlertTriangle, Inbox } from "lucide-react"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

interface Props {
  variant: "empty" | "error"
  title: string
  description?: string
  action?: { label: string; onClick: () => void }
  className?: string
}

export default function StateBanner({ variant, title, description, action, className }: Props) {
  const Icon = variant === "error" ? AlertTriangle : Inbox

  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-2 text-center px-6 py-8",
        className,
      )}
    >
      <Icon
        className={cn("h-8 w-8 mb-1", variant === "error" ? "text-destructive" : "text-muted-foreground")}
      />
      <p className="font-medium text-foreground">{title}</p>
      {description && <p className="text-sm text-muted-foreground max-w-sm">{description}</p>}
      {action && (
        <Button variant="outline" size="sm" className="mt-2" onClick={action.onClick}>
          {action.label}
        </Button>
      )}
    </div>
  )
}
