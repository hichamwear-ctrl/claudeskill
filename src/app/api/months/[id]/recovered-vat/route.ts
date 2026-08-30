import { prisma } from "@/lib/db";
import { requireAdmin, handle, json, HttpError } from "@/lib/http";
import { vatSchema } from "@/lib/validation";
import { recoveredVat } from "@/core/finance";
import { SYSTEM_CATEGORY, RECOVERED_VAT_ALLOWED_NAMES } from "@/lib/categories";

export const runtime = "nodejs";

type Ctx = { params: Promise<{ id: string }> };

// Bouton "Récupérer TVA" : sélection RESTREINTE à Essence / Location Camionnette,
// jamais le revenu. -> ligne POSITIVE. Indépendant du bouton TVA (aucune déduplication).
export async function POST(req: Request, { params }: Ctx) {
  return handle(async () => {
    await requireAdmin();
    const { id: monthId } = await params;
    const parsed = vatSchema.parse(await req.json());

    if (parsed.includeRevenue) {
      throw new HttpError(400, "Le revenu n'est pas éligible à la récupération de TVA");
    }
    if (parsed.lineIds.length === 0) throw new HttpError(400, "Aucun élément sélectionné");

    const lines = await prisma.expenseLine.findMany({
      where: { id: { in: parsed.lineIds }, monthId },
      include: { category: true },
    });
    if (lines.length !== parsed.lineIds.length) {
      throw new HttpError(400, "Une ligne sélectionnée n'appartient pas à ce mois");
    }
    // Restriction serveur : uniquement Essence et Location Camionnette.
    for (const l of lines) {
      if (!RECOVERED_VAT_ALLOWED_NAMES.includes(l.category.name as never)) {
        throw new HttpError(400, "Catégorie non éligible à la récupération de TVA");
      }
    }

    const amount = recoveredVat(lines.map((l) => l.amount)); // fonction pure distincte
    if (amount <= 0) throw new HttpError(400, "TVA récupérée calculée nulle");

    const line = await prisma.expenseLine.create({
      data: { monthId, categoryId: SYSTEM_CATEGORY.TVA_RECUPEREE, amount },
      include: { category: true },
    });
    return json(line, 201);
  });
}
