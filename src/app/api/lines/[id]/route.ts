import { prisma } from "@/lib/db";
import { requireAdmin, handle, json } from "@/lib/http";
import { updateLineSchema } from "@/lib/validation";

export const runtime = "nodejs";

type Ctx = { params: Promise<{ id: string }> };

// Modification d'une ligne : seule la valeur finale est conservée (aucun historique
// de correction — §3.2). Écriture : admin uniquement.
export async function PATCH(req: Request, { params }: Ctx) {
  return handle(async () => {
    await requireAdmin();
    const { id } = await params;
    const { amount } = updateLineSchema.parse(await req.json());
    const line = await prisma.expenseLine.update({
      where: { id },
      data: { amount },
      include: { category: true },
    });
    return json(line);
  });
}

export async function DELETE(_req: Request, { params }: Ctx) {
  return handle(async () => {
    await requireAdmin();
    const { id } = await params;
    await prisma.expenseLine.delete({ where: { id } });
    return json({ ok: true });
  });
}
