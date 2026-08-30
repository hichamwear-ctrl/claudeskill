import { prisma } from "@/lib/db";
import { requireAdmin, handle, json, HttpError } from "@/lib/http";
import { createKharjaLineSchema } from "@/lib/validation";

export const runtime = "nodejs";

type Ctx = { params: Promise<{ id: string }> };

// Ajout d'une ligne au Kharja (Entrée/Sortie + note libre). Écriture : admin.
export async function POST(req: Request, { params }: Ctx) {
  return handle(async () => {
    await requireAdmin();
    const { id: kharjaId } = await params;
    const body = createKharjaLineSchema.parse(await req.json());

    const kharja = await prisma.kharja.findUnique({ where: { id: kharjaId } });
    if (!kharja) throw new HttpError(404, "Kharja introuvable");

    const line = await prisma.kharjaLine.create({ data: { kharjaId, ...body } });
    return json(line, 201);
  });
}
