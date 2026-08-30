import { prisma } from "@/lib/db";
import { requireAuth, handle, json } from "@/lib/http";

export const runtime = "nodejs";

type Ctx = { params: Promise<{ id: string }> };

// Kharja d'un mois + son journal complet + effet net. Lecture : admin + reader.
export async function GET(_req: Request, { params }: Ctx) {
  return handle(async () => {
    await requireAuth();
    const { id: monthId } = await params;
    const kharja = await prisma.kharja.findUnique({
      where: { monthId },
      include: { lines: { orderBy: { createdAt: "asc" } } },
    });
    if (!kharja) return json(null);
    const net = kharja.lines.reduce((s, l) => s + (l.type === "IN" ? l.amount : -l.amount), 0);
    return json({ ...kharja, net });
  });
}
