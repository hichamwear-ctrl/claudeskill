import NextAuth from "next-auth";
import Credentials from "next-auth/providers/credentials";
import bcrypt from "bcryptjs";
import { authConfig } from "./auth.config";
import { prisma } from "./prisma";
import { loginSchema } from "@/lib/validations";

export const { handlers, auth, signIn, signOut } = NextAuth({
  ...authConfig,
  providers: [
    Credentials({
      credentials: {
        email: { label: "Email", type: "email" },
        password: { label: "Mot de passe", type: "password" },
      },
      async authorize(credentials) {
        const parsed = loginSchema.safeParse(credentials);
        if (!parsed.success) return null;

        const { email, password } = parsed.data;
        const user = await prisma.user.findUnique({
          where: { email },
          include: { barberProfile: true },
        });
        if (!user) return null;

        const valid = await bcrypt.compare(password, user.passwordHash);
        if (!valid) return null;

        // Phase 5 — a barber can only sign in once the admin has validated the
        // account, and not while banned/suspended.
        if (user.role === "BARBER" && user.barberProfile) {
          const b = user.barberProfile;
          if (b.approvalStatus === "PENDING")
            throw new Error("Votre compte barber est en attente de validation.");
          if (b.approvalStatus === "REFUSED")
            throw new Error("Votre demande de compte barber a été refusée.");
          if (b.bannedAt) throw new Error("Ce compte a été banni.");
          if (b.suspendedAt) throw new Error("Ce compte est suspendu.");
        }

        return {
          id: user.id,
          email: user.email,
          name: `${user.firstName} ${user.lastName}`,
          image: user.image,
          role: user.role,
          firstName: user.firstName,
          lastName: user.lastName,
        };
      },
    }),
  ],
});
