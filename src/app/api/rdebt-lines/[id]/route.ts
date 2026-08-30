import { prisma } from "@/lib/db";
import { requireAdmin, handle, json } from "@/lib/http";

export const runtime = "nodejs";

type Ctx = { params: Promise<{ id: string }> };

// Suppression d'une ligne du journal R. Écriture : admin uniquement.
export async function DELETE(_req: Request, { params }: Ctx) {
  return handle(async () => {
    await requireAdmin();
    const { id } = await params;
    await prisma.rDebtLine.delete({ where: { id } });
    return json({ ok: true });
  });
}
