import NextAuth from "next-auth";
import { authConfig } from "@/server/auth.config";

export default NextAuth(authConfig).auth;

export const config = {
  // Run on all routes except static assets and API auth endpoints.
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)"],
};
