import NextAuth from "next-auth";
import Credentials from "next-auth/providers/credentials";
import { verify } from "@node-rs/argon2";
import { z } from "zod";
import { prisma } from "./db";

const MAX_FAILED_ATTEMPTS = 5;
const LOCK_MINUTES = 15;

const credentialsSchema = z.object({
  email: z.string().email(),
  password: z.string().min(1),
});

export const { handlers, auth, signIn, signOut } = NextAuth({
  session: { strategy: "jwt", maxAge: 60 * 60 * 8 },
  trustHost: true,
  pages: { signIn: "/login" },
  cookies: {
    sessionToken: {
      name:
        process.env.NODE_ENV === "production"
          ? "__Secure-authjs.session-token"
          : "authjs.session-token",
      options: {
        httpOnly: true,
        sameSite: "strict",
        path: "/",
        secure: process.env.NODE_ENV === "production",
      },
    },
  },
  providers: [
    Credentials({
      credentials: { email: {}, password: {} },
      authorize: async (raw) => {
        const parsed = credentialsSchema.safeParse(raw);
        if (!parsed.success) return null;
        const { email, password } = parsed.data;

        const user = await prisma.user.findUnique({ where: { email } });
        // Réponse identique (null) que l'utilisateur existe ou non : pas de fuite.
        if (!user) return null;

        // Verrouillage anti brute-force encore actif ?
        if (user.lockedUntil && user.lockedUntil > new Date()) {
          return null;
        }

        const ok = await verify(user.passwordHash, password);

        if (!ok) {
          const failed = user.failedLogins + 1;
          const locked = failed >= MAX_FAILED_ATTEMPTS;
          await prisma.user.update({
            where: { id: user.id },
            data: {
              failedLogins: locked ? 0 : failed,
              lockedUntil: locked
                ? new Date(Date.now() + LOCK_MINUTES * 60_000)
                : user.lockedUntil,
            },
          });
          return null;
        }

        // Succès : on réinitialise le compteur.
        if (user.failedLogins !== 0 || user.lockedUntil) {
          await prisma.user.update({
            where: { id: user.id },
            data: { failedLogins: 0, lockedUntil: null },
          });
        }

        return { id: user.id, email: user.email, role: user.role };
      },
    }),
  ],
  callbacks: {
    jwt: ({ token, user }) => {
      if (user) {
        token.role = user.role;
        token.uid = user.id;
      }
      return token;
    },
    session: ({ session, token }) => {
      if (token.uid) session.user.id = token.uid as string;
      if (token.role) session.user.role = token.role as "ADMIN" | "READER";
      return session;
    },
  },
});
