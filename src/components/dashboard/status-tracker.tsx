import type { ReservationStatus } from "@prisma/client";
import { Check } from "lucide-react";
import { STATUS_ORDER, STATUS_META, statusProgress } from "@/lib/status";
import { Progress } from "@/components/ui/misc";
import { cn } from "@/lib/utils";

export function StatusTracker({ status }: { status: ReservationStatus }) {
  if (status === "ANNULEE") {
    return (
      <div className="rounded-xl border border-rose-400/30 bg-rose-400/10 px-4 py-3 text-sm text-rose-400">
        Cette réservation a été annulée.
      </div>
    );
  }

  const currentIndex = STATUS_ORDER.indexOf(status);

  return (
    <div>
      <Progress value={statusProgress(status)} className="mb-5" />
      <ol className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {STATUS_ORDER.map((s, i) => {
          const done = i < currentIndex;
          const current = i === currentIndex;
          return (
            <li key={s} className="flex items-center gap-2">
              <span
                className={cn(
                  "flex size-6 shrink-0 items-center justify-center rounded-full border text-[10px] font-bold transition-colors",
                  done && "border-gold bg-gold text-black",
                  current && "border-gold bg-gold/20 text-gold",
                  !done && !current && "border-border text-muted-foreground",
                )}
              >
                {done ? <Check className="size-3" /> : i + 1}
              </span>
              <span
                className={cn(
                  "text-xs",
                  current ? "font-medium text-foreground" : "text-muted-foreground",
                )}
              >
                {STATUS_META[s].label}
              </span>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
