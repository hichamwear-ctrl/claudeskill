import { z } from "zod";

// Montant en CENTIMES : entier. Le client convertit euros -> centimes avant envoi ;
// le serveur n'accepte jamais de décimale.
export const centsPositive = z.number().int().positive();
export const centsNonNegative = z.number().int().nonnegative();

export const createMonthSchema = z.object({
  label: z.string().trim().min(1).max(100),
  clientPayment: centsNonNegative,
});

export const updateMonthSchema = z.object({
  label: z.string().trim().min(1).max(100).optional(),
  clientPayment: centsNonNegative.optional(),
});

export const createLineSchema = z.object({
  categoryId: z.string().min(1),
  amount: centsPositive,
});

export const updateLineSchema = z.object({
  amount: centsPositive,
});

export const createCategorySchema = z.object({
  name: z.string().trim().min(1).max(60),
  icon: z.string().trim().min(1).max(60),
  type: z.enum(["SUBTRACTION", "ADDITION"]),
});

// TVA / TVA récupérée : liste d'identifiants d'éléments cochés + le revenu éventuel.
export const vatSchema = z.object({
  includeRevenue: z.boolean().default(false),
  lineIds: z.array(z.string().min(1)).default([]),
});

export const createKharjaSchema = z.object({
  monthId: z.string().min(1),
});

export const createKharjaLineSchema = z.object({
  type: z.enum(["IN", "OUT"]),
  amount: centsPositive,
  note: z.string().trim().max(500).default(""),
});

export const updateKharjaLineSchema = z.object({
  type: z.enum(["IN", "OUT"]).optional(),
  amount: centsPositive.optional(),
  note: z.string().trim().max(500).optional(),
});

export const updateRDebtBaseSchema = z.object({
  baseAmount: centsNonNegative,
});

export const createRDebtLineSchema = z
  .object({
    type: z.enum(["INCREASE", "REPAYMENT"]),
    paymentMethod: z.enum(["CASH", "TRANSFER"]).optional(),
    amountGross: centsPositive,
  })
  .refine((v) => v.type === "INCREASE" || v.paymentMethod !== undefined, {
    message: "Un remboursement exige un mode de paiement (cash ou virement)",
    path: ["paymentMethod"],
  });
