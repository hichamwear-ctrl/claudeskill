import { prisma } from "@/lib/db";
import { requireAdmin, requireAuth, handle, json, HttpError } from "@/lib/http";
import { updateMonthSchema } from "@/lib/validation";
import { monthNetRemainder } from "@/core/finance";

export const runtime = "nodejs";

type Ctx = { params: Promise<{ id: string }> };

// Détail d'un mois : revenu + historique complet + reste net.
export async function GET(_req: Request, { params }: Ctx) {
  return handle(async () => {
    await requireAuth();
    const { id } = await params;
    const month = await prisma.month.findUnique({
      where: { id },
      include: {
        expenses: { include: { category: true }, orderBy: { createdAt: "asc" } },
        kharja: { include: { lines: { orderBy: { createdAt: "asc" } } } },
      },
    });
    if (!month) throw new HttpError(404, "Mois introuvable");
    const remainder = monthNetRemainder(
      month.clientPayment,
      month.expenses.map((e) => ({ amount: e.amount, type: e.category.type })),
    );
    return json({ ...month, remainder });
  });
}

export async function PATCH(req: Request, { params }: Ctx) {
  return handle(async () => {
    await requireAdmin();
    const { id } = await params;
    const body = updateMonthSchema.parse(await req.json());
    const month = await prisma.month.update({ where: { id }, data: body });
    return json(month);
  });
}

export async function DELETE(_req: Request, { params }: Ctx) {
  return handle(async () => {
    await requireAdmin();
    const { id } = await params;
    await prisma.month.delete({ where: { id } });
    return json({ ok: true });
  });
}
