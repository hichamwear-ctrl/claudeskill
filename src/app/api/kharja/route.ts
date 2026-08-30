import { prisma } from "@/lib/db";
import { requireAdmin, handle, json, HttpError } from "@/lib/http";
import { createKharjaSchema } from "@/lib/validation";

export const runtime = "nodejs";

// Création d'un Kharja rattaché à un mois existant (un seul par mois — §5).
export async function POST(req: Request) {
  return handle(async () => {
    await requireAdmin();
    const { monthId } = createKharjaSchema.parse(await req.json());

    const month = await prisma.month.findUnique({ where: { id: monthId } });
    if (!month) throw new HttpError(404, "Mois introuvable");

    const existing = await prisma.kharja.findUnique({ where: { monthId } });
    if (existing) throw new HttpError(409, "Ce mois a déjà un Kharja");

    const kharja = await prisma.kharja.create({ data: { monthId } });
    return json(kharja, 201);
  });
}
