import { prisma } from "@/lib/db";
import { requireAdmin, requireAuth, handle, json, HttpError } from "@/lib/http";
import { updateRDebtBaseSchema } from "@/lib/validation";
import { rDebtBalance } from "@/core/finance";

export const runtime = "nodejs";

// Solde R + journal complet. Lecture : admin + reader (R voit son propre onglet).
export async function GET() {
  return handle(async () => {
    await requireAuth();
    const rdebt = await prisma.rDebt.findFirst({
      include: { lines: { orderBy: { createdAt: "asc" } } },
    });
    if (!rdebt) throw new HttpError(404, "Dette R non initialisée");
    const balance = rDebtBalance(
      rdebt.baseAmount,
      rdebt.lines.map((l) => ({ type: l.type, amountNet: l.amountNet })),
    );
    return json({ id: rdebt.id, baseAmount: rdebt.baseAmount, balance, lines: rdebt.lines });
  });
}

// Modification du montant de base. Écriture : admin uniquement.
export async function PATCH(req: Request) {
  return handle(async () => {
    await requireAdmin();
    const { baseAmount } = updateRDebtBaseSchema.parse(await req.json());
    const rdebt = await prisma.rDebt.findFirst();
    if (!rdebt) throw new HttpError(404, "Dette R non initialisée");
    const updated = await prisma.rDebt.update({ where: { id: rdebt.id }, data: { baseAmount } });
    return json(updated);
  });
}
