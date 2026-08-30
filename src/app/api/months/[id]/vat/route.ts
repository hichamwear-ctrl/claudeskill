import { prisma } from "@/lib/db";
import { requireAdmin, handle, json, HttpError } from "@/lib/http";
import { vatSchema } from "@/lib/validation";
import { vat } from "@/core/finance";
import { SYSTEM_CATEGORY } from "@/lib/categories";

export const runtime = "nodejs";

type Ctx = { params: Promise<{ id: string }> };

// Bouton "TVA" : somme libre (revenu et/ou dépenses cochées) -> ligne NÉGATIVE.
export async function POST(req: Request, { params }: Ctx) {
  return handle(async () => {
    await requireAdmin();
    const { id: monthId } = await params;
    const { includeRevenue, lineIds } = vatSchema.parse(await req.json());

    const month = await prisma.month.findUnique({ where: { id: monthId } });
    if (!month) throw new HttpError(404, "Mois introuvable");

    const selected: number[] = [];
    if (includeRevenue) selected.push(month.clientPayment);

    if (lineIds.length > 0) {
      const lines = await prisma.expenseLine.findMany({
        where: { id: { in: lineIds }, monthId },
      });
      if (lines.length !== lineIds.length) {
        throw new HttpError(400, "Une ligne sélectionnée n'appartient pas à ce mois");
      }
      for (const l of lines) selected.push(l.amount);
    }

    if (selected.length === 0) throw new HttpError(400, "Aucun élément sélectionné");

    const amount = vat(selected); // fonction pure, source unique
    if (amount <= 0) throw new HttpError(400, "TVA calculée nulle");

    const line = await prisma.expenseLine.create({
      data: { monthId, categoryId: SYSTEM_CATEGORY.TVA, amount },
      include: { category: true },
    });
    return json(line, 201);
  });
}
