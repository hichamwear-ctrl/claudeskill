import { redirect } from "next/navigation";
import type { Role } from "@prisma/client";
import { auth } from "./auth";

/** Returns the session or redirects to /login. */
export async function requireAuth() {
  const session = await auth();
  if (!session?.user) redirect("/login");
  return session;
}

/** Ensures the user has one of the allowed roles. */
export async function requireRole(roles: Role[]) {
  const session = await requireAuth();
  if (!roles.includes(session.user.role)) {
    redirect(dashboardPath(session.user.role));
  }
  return session;
}

export function dashboardPath(role: Role): string {
  switch (role) {
    case "ADMIN":
      return "/admin";
    case "BARBER":
      return "/barber";
    default:
      return "/client";
  }
}
