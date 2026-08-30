import { prisma } from "@/lib/db";
import { requireAdmin, handle, json } from "@/lib/http";
import { updateKharjaLineSchema } from "@/lib/validation";

export const runtime = "nodejs";

type Ctx = { params: Promise<{ id: string }> };

// Le journal Kharja conserve chaque ligne en détail (§9). Écriture : admin.
export async function PATCH(req: Request, { params }: Ctx) {
  return handle(async () => {
    await requireAdmin();
    const { id } = await params;
    const body = updateKharjaLineSchema.parse(await req.json());
    const line = await prisma.kharjaLine.update({ where: { id }, data: body });
    return json(line);
  });
}

export async function DELETE(_req: Request, { params }: Ctx) {
  return handle(async () => {
    await requireAdmin();
    const { id } = await params;
    await prisma.kharjaLine.delete({ where: { id } });
    return json({ ok: true });
  });
}
