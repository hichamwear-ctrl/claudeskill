import { z } from "zod";

export const loginSchema = z.object({
  email: z.string().email("Email invalide"),
  password: z.string().min(1, "Mot de passe requis"),
});

export const registerSchema = z
  .object({
    firstName: z.string().min(2, "Prénom trop court"),
    lastName: z.string().min(2, "Nom trop court"),
    username: z.string().min(3, "Pseudo trop court").optional().or(z.literal("")),
    email: z.string().email("Email invalide"),
    phone: z.string().min(6, "Téléphone invalide").optional().or(z.literal("")),
    password: z.string().min(8, "8 caractères minimum"),
    confirmPassword: z.string(),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: "Les mots de passe ne correspondent pas",
    path: ["confirmPassword"],
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

export const reviewSchema = z.object({
  reservationId: z.string(),
  rating: z.number().int().min(1).max(5),
  comment: z.string().max(1000).optional(),
});

export type RegisterInput = z.infer<typeof registerSchema>;
export type LoginInput = z.infer<typeof loginSchema>;
export type CreateReservationInput = z.infer<typeof createReservationSchema>;
