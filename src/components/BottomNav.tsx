"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

export function BottomNav() {
  const pathname = usePathname();
  const onR = pathname.startsWith("/r");
  return (
    <nav className="bottom-nav">
      <Link href="/" className={`nav-item ${!onR ? "active" : ""}`}>
        <span className="nav-icon" aria-hidden>
          🗓️
        </span>
        Mois
      </Link>
      <Link href="/r" className={`nav-item ${onR ? "active" : ""}`}>
        <span className="nav-icon" aria-hidden>
          👥
        </span>
        R
      </Link>
    </nav>
  );
}
