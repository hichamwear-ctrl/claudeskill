import type { NextAuthConfig } from "next-auth";

/**
 * Edge-safe auth config (no Prisma / bcrypt here) used by middleware.
 * Route-protection logic lives in `authorized`.
 */
export const authConfig = {
  pages: {
    signIn: "/login",
  },
  session: { strategy: "jwt" },
  providers: [], // real providers added in auth.ts (Node runtime)
  callbacks: {
    authorized({ auth, request: { nextUrl } }) {
      const isLoggedIn = !!auth?.user;
      const role = auth?.user?.role;
      const path = nextUrl.pathname;

      const protectedPrefixes = ["/client", "/barber", "/admin"];
      const isProtected = protectedPrefixes.some((p) => path.startsWith(p));

      if (isProtected && !isLoggedIn) return false;

      if (isLoggedIn) {
        if (path.startsWith("/admin") && role !== "ADMIN") return false;
        if (path.startsWith("/barber") && role !== "BARBER" && role !== "ADMIN")
          return false;
      }
      return true;
    },
    jwt({ token, user }) {
      if (user) {
        token.id = user.id;
        token.role = user.role;
        token.firstName = user.firstName;
        token.lastName = user.lastName;
      }
      return token;
    },
    session({ session, token }) {
      if (session.user) {
        session.user.id = token.id as string;
        session.user.role = token.role as "CLIENT" | "BARBER" | "ADMIN";
        session.user.firstName = token.firstName as string;
        session.user.lastName = token.lastName as string;
      }
      return session;
    },
  },
} satisfies NextAuthConfig;
