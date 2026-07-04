import Link from "next/link";
import { cn } from "@/lib/utils";

export function Logo({
  className,
  href = "/",
}: {
  className?: string;
  href?: string;
}) {
  return (
    <Link href={href} className={cn("group flex items-center gap-2.5", className)}>
      <span className="relative flex size-9 items-center justify-center rounded-xl bg-gold-gradient text-black shadow-lg">
        <svg
          viewBox="0 0 24 24"
          fill="none"
          className="size-5"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M4 4l6 6" />
          <circle cx="6" cy="6" r="2.5" />
          <path d="M20 4l-6 6" />
          <circle cx="18" cy="6" r="2.5" />
          <path d="M12 12v8" />
          <path d="M9 20h6" />
        </svg>
      </span>
      <span className="text-lg font-semibold tracking-tight">
        Barber<span className="text-gold-gradient font-bold">Home</span>
      </span>
    </Link>
  );
}
