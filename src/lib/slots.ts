export interface HourSlot {
  /** "16:00" */
  start: string;
  /** "16 h – 17 h" */
  label: string;
  disabled: boolean;
}

export interface WorkingRange {
  startTime: string; // "09:00"
  endTime: string; // "18:00"
}

export function toDateInput(d: Date): string {
  return d.toISOString().slice(0, 10);
}

export function hourRangeLabel(hour: number): string {
  const h2 = (hour + 1) % 24;
  return `${hour} h – ${h2} h`;
}

/**
 * Union of the whole hours covered by a set of barber working ranges.
 * An hour H is bookable if at least one range covers [H:00, H+1:00).
 * Pure & unit-tested — the availability engine's core.
 */
export function availableHourStarts(ranges: WorkingRange[]): number[] {
  const hours = new Set<number>();
  for (const r of ranges) {
    const start = parseInt(r.startTime.slice(0, 2), 10);
    const end = parseInt(r.endTime.slice(0, 2), 10);
    if (Number.isNaN(start) || Number.isNaN(end)) continue;
    for (let h = start; h < end; h++) hours.add(h);
  }
  return [...hours].sort((a, b) => a - b);
}

/**
 * Turns available hour starts into UI slots, disabling past hours (with a lead
 * time) when the date is today.
 */
export function buildHourSlots(
  date: string,
  hourStarts: number[],
  { leadMinutes = 60 } = {},
): HourSlot[] {
  const now = new Date();
  const isToday = date === toDateInput(now);
  return hourStarts.map((h) => {
    const start = `${String(h).padStart(2, "0")}:00`;
    let disabled = false;
    if (isToday) {
      const slotDate = new Date(`${date}T${start}:00`);
      disabled = slotDate.getTime() < now.getTime() + leadMinutes * 60 * 1000;
    }
    return { start, label: hourRangeLabel(h), disabled };
  });
}

/** Next N selectable days starting today. */
export function upcomingDays(count = 14): { value: string; label: string }[] {
  const days: { value: string; label: string }[] = [];
  const fmt = new Intl.DateTimeFormat("fr-BE", {
    weekday: "short",
    day: "numeric",
    month: "short",
  });
  for (let i = 0; i < count; i++) {
    const d = new Date();
    d.setDate(d.getDate() + i);
    days.push({ value: toDateInput(d), label: fmt.format(d) });
  }
  return days;
}
