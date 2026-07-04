/** Generates 30-minute booking slots between opening and closing hours. */
export function generateSlots(
  date: string,
  { open = 9, close = 19, stepMin = 30 } = {},
): { time: string; disabled: boolean }[] {
  const slots: { time: string; disabled: boolean }[] = [];
  const now = new Date();
  const isToday = date === toDateInput(now);

  for (let h = open; h < close; h++) {
    for (let m = 0; m < 60; m += stepMin) {
      const time = `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`;
      let disabled = false;
      if (isToday) {
        const slotDate = new Date(`${date}T${time}:00`);
        // Require at least 60 min lead time.
        disabled = slotDate.getTime() < now.getTime() + 60 * 60 * 1000;
      }
      slots.push({ time, disabled });
    }
  }
  return slots;
}

export function toDateInput(d: Date): string {
  return d.toISOString().slice(0, 10);
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
