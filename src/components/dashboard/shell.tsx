"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { signOut } from "next-auth/react";
import { motion, AnimatePresence } from "framer-motion";
import {
  LogOut,
  Menu,
  X,
  LayoutDashboard,
  CalendarPlus,
  CalendarClock,
  CalendarRange,
  ReceiptText,
  MapPin,
  User,
  Users,
  History,
  Wallet,
  Scissors,
  Star,
  Tag,
  CreditCard,
  Clock,
  Sparkles,
  Heart,
  type LucideIcon,
} from "lucide-react";
import { Logo } from "@/components/logo";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { cn, getInitials } from "@/lib/utils";

/**
 * Icon registry keyed by name. Nav items reference icons by string so the
 * (server) dashboard layouts never pass function/component values across the
 * server → client boundary (which React cannot serialize).
 */
const NAV_ICONS = {
  LayoutDashboard,
  CalendarPlus,
  CalendarClock,
  CalendarRange,
  ReceiptText,
  MapPin,
  User,
  Users,
  History,
  Wallet,
  Scissors,
  Star,
  Tag,
  CreditCard,
  Clock,
  Sparkles,
  Heart,
} satisfies Record<string, LucideIcon>;

export type NavIconName = keyof typeof NAV_ICONS;

export interface NavItem {
  href: string;
  label: string;
  icon: NavIconName;
}

interface ShellProps {
  nav: NavItem[];
  user: {
    firstName: string;
    lastName: string;
    email?: string | null;
    image?: string | null;
    role: string;
  };
  roleLabel: string;
  children: React.ReactNode;
}

export function DashboardShell({ nav, user, roleLabel, children }: ShellProps) {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);

  const sidebar = (
    <div className="flex h-full flex-col">
      <div className="flex h-16 items-center px-6">
        <Logo href="#" />
      </div>
      <nav className="flex-1 space-y-1 px-3 py-4">
        {nav.map((item) => {
          const active =
            pathname === item.href ||
            (item.href !== nav[0].href && pathname.startsWith(item.href));
          const Icon = NAV_ICONS[item.icon];
          return (
            <Link
              key={item.href}
              href={item.href}
              onClick={() => setOpen(false)}
              className={cn(
                "flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors",
                active
                  ? "bg-gold/10 text-gold"
                  : "text-muted-foreground hover:bg-secondary hover:text-foreground",
              )}
            >
              <Icon className="size-5" />
              {item.label}
            </Link>
          );
        })}
      </nav>
      <div className="border-t border-border p-3">
        <div className="flex items-center gap-3 rounded-xl px-3 py-2">
          <Avatar>
            {user.image && <AvatarImage src={user.image} alt="" />}
            <AvatarFallback>
              {getInitials(user.firstName, user.lastName)}
            </AvatarFallback>
          </Avatar>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium">
              {user.firstName} {user.lastName}
            </p>
            <p className="truncate text-xs text-muted-foreground">{roleLabel}</p>
          </div>
        </div>
        <Button
          variant="ghost"
          size="sm"
          className="mt-1 w-full justify-start text-muted-foreground"
          onClick={() => signOut({ callbackUrl: "/" })}
        >
          <LogOut className="size-4" />
          Déconnexion
        </Button>
      </div>
    </div>
  );

  // On mobile we surface the first 3 destinations as bottom tabs; the rest live
  // behind the "Menu" tab (the drawer). Keeps the screen uncluttered.
  const tabs = nav.slice(0, 3);
  const isActive = (href: string) =>
    pathname === href || (href !== nav[0].href && pathname.startsWith(href));

  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[260px_1fr]">
      {/* Desktop sidebar */}
      <aside className="hidden border-r border-border bg-card/40 lg:block">
        <div className="sticky top-0 h-screen">{sidebar}</div>
      </aside>

      {/* Mobile top bar: logo + avatar */}
      <div className="sticky top-0 z-30 flex items-center justify-between border-b border-border bg-background/90 px-4 py-3 backdrop-blur lg:hidden">
        <Logo href="#" />
        <button onClick={() => setOpen(true)} aria-label="Ouvrir le menu">
          <Avatar className="size-9">
            {user.image && <AvatarImage src={user.image} alt="" />}
            <AvatarFallback>
              {getInitials(user.firstName, user.lastName)}
            </AvatarFallback>
          </Avatar>
        </button>
      </div>

      {/* Mobile drawer (full navigation) */}
      <AnimatePresence>
        {open && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 z-40 bg-black/60 lg:hidden"
              onClick={() => setOpen(false)}
            />
            <motion.aside
              initial={{ x: "-100%" }}
              animate={{ x: 0 }}
              exit={{ x: "-100%" }}
              transition={{ type: "spring", damping: 26, stiffness: 240 }}
              className="fixed inset-y-0 left-0 z-50 w-72 border-r border-border bg-card lg:hidden"
            >
              <button
                className="absolute right-4 top-4 text-muted-foreground"
                onClick={() => setOpen(false)}
                aria-label="Fermer le menu"
              >
                <X className="size-5" />
              </button>
              {sidebar}
            </motion.aside>
          </>
        )}
      </AnimatePresence>

      {/* Extra bottom padding on mobile so the tab bar never overlaps content */}
      <main className="min-w-0 pb-24 lg:pb-0">{children}</main>

      {/* Mobile bottom tab bar (dark/gold) */}
      <nav
        aria-label="Navigation"
        className="fixed inset-x-0 bottom-0 z-40 lg:hidden"
      >
        <div className="glass mx-3 mb-3 flex items-stretch justify-around gap-1 rounded-2xl px-2 py-2 premium-shadow">
          {tabs.map((item) => {
            const Icon = NAV_ICONS[item.icon];
            const active = isActive(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "flex flex-1 flex-col items-center gap-1 rounded-xl px-1 py-1.5 text-[11px] font-medium transition-colors",
                  active ? "bg-gold/10 text-gold" : "text-muted-foreground",
                )}
              >
                <Icon className="size-5" />
                <span className="max-w-full truncate">
                  {item.label.split(" ")[0]}
                </span>
              </Link>
            );
          })}
          <button
            onClick={() => setOpen(true)}
            className="flex flex-1 flex-col items-center gap-1 rounded-xl px-1 py-1.5 text-[11px] font-medium text-muted-foreground transition-colors"
          >
            <Menu className="size-5" />
            <span>Menu</span>
          </button>
        </div>
      </nav>
    </div>
  );
}
