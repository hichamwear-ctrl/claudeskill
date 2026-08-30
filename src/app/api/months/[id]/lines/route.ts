import { prisma } from "@/lib/db";
import { requireAdmin, handle, json, HttpError } from "@/lib/http";
import { createLineSchema } from "@/lib/validation";

export const runtime = "nodejs";

type Ctx = { params: Promise<{ id: string }> };

// Ajout d'une ligne (dépense/addition) au mois. Écriture : admin uniquement.
export async function POST(req: Request, { params }: Ctx) {
  return handle(async () => {
    await requireAdmin();
    const { id: monthId } = await params;
    const { categoryId, amount } = createLineSchema.parse(await req.json());

    const [month, category] = await Promise.all([
      prisma.month.findUnique({ where: { id: monthId } }),
      prisma.category.findUnique({ where: { id: categoryId } }),
    ]);
    if (!month) throw new HttpError(404, "Mois introuvable");
    if (!category) throw new HttpError(404, "Catégorie introuvable");
    // Les catégories internes (TVA / TVA récupérée) passent par leurs endpoints dédiés.
    if (category.isSystem) throw new HttpError(400, "Catégorie réservée au calcul TVA");

    const line = await prisma.expenseLine.create({
      data: { monthId, categoryId, amount },
      include: { category: true },
    });
    return json(line, 201);
  });
}
