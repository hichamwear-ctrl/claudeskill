"use client";

import { useState, useId } from "react";
import { motion, AnimatePresence, useReducedMotion } from "framer-motion";
import { ChevronDown } from "lucide-react";
import { SectionHeading } from "@/components/marketing/section-heading";
import { FAQ } from "@/lib/marketing-content";
import { cn } from "@/lib/utils";

export function FaqSection() {
  const [open, setOpen] = useState<number | null>(0);
  const reduce = useReducedMotion();
  const baseId = useId();

  return (
    <section id="faq" className="border-t border-border/60 bg-secondary/20 py-24">
      <div className="container max-w-3xl">
        <SectionHeading eyebrow="FAQ" title="Vos questions, nos réponses" />
        <dl className="mt-12 divide-y divide-border overflow-hidden rounded-2xl border border-border bg-card">
          {FAQ.map((item, i) => {
            const isOpen = open === i;
            const btnId = `${baseId}-q-${i}`;
            const panelId = `${baseId}-a-${i}`;
            return (
              <div key={item.q}>
                <dt>
                  <button
                    id={btnId}
                    aria-expanded={isOpen}
                    aria-controls={panelId}
                    onClick={() => setOpen(isOpen ? null : i)}
                    className="flex w-full items-center justify-between gap-4 px-5 py-5 text-left transition-colors hover:bg-secondary/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gold/40"
                  >
                    <span className="font-medium">{item.q}</span>
                    <ChevronDown
                      className={cn(
                        "size-5 shrink-0 text-gold transition-transform duration-300",
                        isOpen && "rotate-180",
                      )}
                    />
                  </button>
                </dt>
                <AnimatePresence initial={false}>
                  {isOpen && (
                    <motion.dd
                      id={panelId}
                      role="region"
                      aria-labelledby={btnId}
                      initial={reduce ? undefined : { height: 0, opacity: 0 }}
                      animate={{ height: "auto", opacity: 1 }}
                      exit={reduce ? undefined : { height: 0, opacity: 0 }}
                      transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
                      className="overflow-hidden"
                    >
                      <p className="px-5 pb-5 text-sm text-muted-foreground">
                        {item.a}
                      </p>
                    </motion.dd>
                  )}
                </AnimatePresence>
              </div>
            );
          })}
        </dl>
      </div>
    </section>
  );
}
