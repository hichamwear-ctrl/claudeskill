"use client";

import { motion } from "framer-motion";
import { formatCurrency } from "@/lib/utils";

interface Point {
  label: string;
  count: number;
  revenue: number;
}

export function WeeklyChart({ data }: { data: Point[] }) {
  const max = Math.max(...data.map((d) => d.count), 1);

  return (
    <div>
      <div className="flex items-end justify-between gap-3" style={{ height: 200 }}>
        {data.map((d, i) => (
          <div key={i} className="flex flex-1 flex-col items-center gap-2">
            <div className="flex w-full flex-1 items-end">
              <motion.div
                initial={{ height: 0 }}
                animate={{ height: `${(d.count / max) * 100}%` }}
                transition={{ delay: i * 0.06, duration: 0.5, ease: "easeOut" }}
                className="group relative w-full rounded-t-lg bg-gold-gradient"
                style={{ minHeight: d.count > 0 ? 6 : 0 }}
              >
                <span className="absolute -top-6 left-1/2 -translate-x-1/2 whitespace-nowrap rounded bg-secondary px-1.5 py-0.5 text-[10px] opacity-0 transition-opacity group-hover:opacity-100">
                  {d.count} · {formatCurrency(d.revenue)}
                </span>
              </motion.div>
            </div>
            <span className="text-xs capitalize text-muted-foreground">
              {d.label}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
