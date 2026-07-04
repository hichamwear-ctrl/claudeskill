import { cn } from "@/lib/utils";

export function SectionHeading({
  eyebrow,
  title,
  subtitle,
  align = "center",
  id,
}: {
  eyebrow: string;
  title: React.ReactNode;
  subtitle?: string;
  align?: "center" | "left";
  id?: string;
}) {
  return (
    <div
      className={cn(
        align === "center" ? "mx-auto max-w-2xl text-center" : "max-w-xl",
      )}
    >
      <p className="text-sm font-semibold uppercase tracking-widest text-gold">
        {eyebrow}
      </p>
      <h2
        id={id}
        className="mt-3 font-display text-4xl font-bold tracking-tight sm:text-5xl"
      >
        {title}
      </h2>
      {subtitle && (
        <p className="mt-4 text-pretty text-muted-foreground">{subtitle}</p>
      )}
    </div>
  );
}
