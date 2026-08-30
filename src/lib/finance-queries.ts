import { prisma } from "./db";
import {
  monthNetRemainder,
  globalCapital,
  rDebtBalance,
  type MonthLine,
  type KharjaLine as PureKharjaLine,
  type RDebtLine as PureRDebtLine,
} from "@/core/finance";

/**
 * Point unique où la lecture DB rencontre les fonctions de calcul pures.
 * Aucune arithmétique métier n'est réécrite ici : on ne fait que composer.
 */

export async function computeMonthRemainder(monthId: string): Promise<number> {
  const month = await prisma.month.findUnique({
    where: { id: monthId },
    include: { expenses: { include: { category: true } } },
  });
  if (!month) return 0;
  const lines: MonthLine[] = month.expenses.map((e) => ({
    amount: e.amount,
    type: e.category.type,
  }));
  return monthNetRemainder(month.clientPayment, lines);
}

/** capital_global = Σ(reste de chaque mois) + Σ(Kharja : entrées − sorties). */
export async function computeGlobalCapital(): Promise<number> {
  const months = await prisma.month.findMany({
    include: { expenses: { include: { category: true } } },
  });
  const remainders = months.map((m) =>
    monthNetRemainder(
      m.clientPayment,
      m.expenses.map((e) => ({ amount: e.amount, type: e.category.type })),
    ),
  );
  const kharjaLines = await prisma.kharjaLine.findMany();
  const pureKharja: PureKharjaLine[] = kharjaLines.map((k) => ({
    type: k.type,
    amount: k.amount,
  }));
  return globalCapital(remainders, pureKharja);
}

/** Décomposition mois par mois pour la vue "Détail" du capital global. */
export async function computeCapitalBreakdown() {
  const months = await prisma.month.findMany({
    orderBy: { createdAt: "asc" },
    include: { expenses: { include: { category: true } }, kharja: { include: { lines: true } } },
  });
  return months.map((m) => {
    const remainder = monthNetRemainder(
      m.clientPayment,
      m.expenses.map((e) => ({ amount: e.amount, type: e.category.type })),
    );
    const kharjaNet =
      m.kharja?.lines.reduce((s, l) => s + (l.type === "IN" ? l.amount : -l.amount), 0) ?? 0;
    return { id: m.id, label: m.label, remainder, kharjaNet };
  });
}

/** solde_R — strictement isolé du capital et des mois. */
export async function computeRDebtBalance(): Promise<number> {
  const rdebt = await prisma.rDebt.findFirst({ include: { lines: true } });
  if (!rdebt) return 0;
  const lines: PureRDebtLine[] = rdebt.lines.map((l) => ({
    type: l.type,
    amountNet: l.amountNet,
  }));
  return rDebtBalance(rdebt.baseAmount, lines);
}
