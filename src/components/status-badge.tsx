import type { ReservationStatus } from "@prisma/client";
import { Badge } from "@/components/ui/badge";
import { STATUS_META } from "@/lib/status";
import { cn } from "@/lib/utils";

export function StatusBadge({
  status,
  className,
}: {
  status: ReservationStatus;
  className?: string;
}) {
  const meta = STATUS_META[status];
  return (
    <Badge className={cn(meta.color, className)}>
      <span className="mr-1.5 inline-block size-1.5 rounded-full bg-current" />
      {meta.label}
    </Badge>
  );
}
