import { z } from "zod";

export const loginSchema = z.object({
  email: z.string().email("Email invalide"),
  password: z.string().min(1, "Mot de passe requis"),
});

export const barberLevels = ["JUNIOR", "CONFIRME", "EXPERT"] as const;

export const registerSchema = z
  .object({
    firstName: z.string().min(2, "Prénom trop court"),
    lastName: z.string().min(2, "Nom trop court"),
    username: z.string().min(3, "Pseudo trop court").optional().or(z.literal("")),
    email: z.string().email("Email invalide"),
    phone: z.string().min(6, "Téléphone invalide").optional().or(z.literal("")),
    password: z.string().min(8, "8 caractères minimum"),
    confirmPassword: z.string(),
    // Phase 5 — account type + barber onboarding dossier.
    role: z.enum(["CLIENT", "BARBER"]).default("CLIENT"),
    social: z.string().optional().or(z.literal("")),
    yearsExperience: z.coerce.number().int().min(0).max(60).optional(),
    level: z.enum(barberLevels).optional(),
    bio: z.string().max(1000).optional().or(z.literal("")),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: "Les mots de passe ne correspondent pas",
    path: ["confirmPassword"],
  })
  .superRefine((data, ctx) => {
    if (data.role !== "BARBER") return;
    // Barbers must supply a full application dossier.
    if (!data.phone || data.phone.length < 6)
      ctx.addIssue({ code: "custom", path: ["phone"], message: "Téléphone requis" });
    if (!data.social)
      ctx.addIssue({
        code: "custom",
        path: ["social"],
        message: "Instagram ou Snapchat requis",
      });
    if (data.yearsExperience == null)
      ctx.addIssue({
        code: "custom",
        path: ["yearsExperience"],
        message: "Années d'expérience requises",
      });
    if (!data.level)
      ctx.addIssue({ code: "custom", path: ["level"], message: "Niveau requis" });
    if (!data.bio)
      ctx.addIssue({ code: "custom", path: ["bio"], message: "Biographie requise" });
  });

export const forgotPasswordSchema = z.object({
  email: z.string().email("Email invalide"),
});

export const addressSchema = z.object({
  label: z.string().min(1).default("Domicile"),
  street: z.string().min(2, "Rue requise"),
  number: z.string().optional().or(z.literal("")),
  city: z.string().min(2, "Ville requise"),
  postalCode: z.string().min(4, "Code postal requis"),
  country: z.string().default("Belgique"),
  latitude: z.number().nullable().optional(),
  longitude: z.number().nullable().optional(),
});

export const personSchema = z.object({
  type: z.enum(["ADULTE", "ENFANT"]),
  service: z.enum(["ADULTE_COUPE", "ADULTE_COUPE_BARBE", "ENFANT_COUPE"]),
  label: z.string().optional(),
});

export const createReservationSchema = z.object({
  addressId: z.string().optional(),
  address: addressSchema.optional(),
  scheduledAt: z.string().datetime().or(z.string().min(1)),
  persons: z.array(personSchema).min(1, "Ajoutez au moins une personne"),
  paymentMethod: z.enum(["ONLINE", "ON_SITE"]).default("ON_SITE"),
  promoCode: z.string().optional(),
  notes: z.string().optional(),
  digicode: z.string().optional(),
  floor: z.string().optional(),
  parking: z.string().optional(),
});

export const updateStatusSchema = z.object({
  status: z.enum([
    "DEMANDE_ENVOYEE",
    "ACCEPTEE",
    "BARBER_ATTRIBUE",
    "EN_ROUTE",
    "ARRIVE",
    "EN_COURS",
    "TERMINEE",
    "ANNULEE",
  ]),
});

// Accept a hosted URL or an inline data: URL, capped to ~4 MB of base64.
export const imageInput = z
  .string()
  .max(5_600_000)
  .refine(
    (v) => /^https?:\/\//.test(v) || /^data:image\/[a-z+]+;base64,/.test(v),
    "Image invalide",
  );

export const reviewSchema = z.object({
  reservationId: z.string(),
  rating: z.number().int().min(1).max(5),
  comment: z.string().max(1000).optional(),
  photo: imageInput.optional().or(z.literal("")),
});

// Phase 5 — client validates or rejects the barber who accepted.
export const confirmBarberSchema = z.object({
  decision: z.enum(["CONFIRM", "REFUSE"]),
});

// Phase 5 — private chat message.
export const messageSchema = z.object({
  body: z.string().min(1, "Message vide").max(2000),
});

// Phase 5 — end-of-order report ("signaler un problème" / "besoin d'aide").
export const reportSchema = z.object({
  reservationId: z.string().optional(),
  barberId: z.string().optional(),
  type: z.enum(["PROBLEM", "HELP"]),
  message: z.string().min(1, "Message requis").max(2000),
});

// Phase 5 — barber edits their public profile.
export const barberProfileSchema = z.object({
  bio: z.string().max(1000).optional().or(z.literal("")),
  yearsExperience: z.coerce.number().int().min(0).max(60).optional(),
  level: z.enum(barberLevels).optional(),
  instagram: z.string().max(120).optional().or(z.literal("")),
  snapchat: z.string().max(120).optional().or(z.literal("")),
});

// Phase 5 — barber adds a portfolio photo.
export const barberPhotoSchema = z.object({
  url: imageInput,
  caption: z.string().max(120).optional().or(z.literal("")),
});

// Phase 5 — admin moderation action on a barber.
export const barberModerationSchema = z.object({
  barberId: z.string(),
  action: z.enum(["APPROVE", "REFUSE", "BAN", "UNBAN", "SUSPEND", "UNSUSPEND", "DELETE"]),
});

// Phase 5 — admin note attached to a barber.
export const adminNoteSchema = z.object({
  barberId: z.string(),
  body: z.string().min(1).max(2000),
});

export type RegisterInput = z.infer<typeof registerSchema>;
export type LoginInput = z.infer<typeof loginSchema>;
export type CreateReservationInput = z.infer<typeof createReservationSchema>;
