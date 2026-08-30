import { prisma } from "@/lib/db";
import { requireAdmin, requireAuth, handle, json } from "@/lib/http";
import { createMonthSchema } from "@/lib/validation";
import { monthNetRemainder } from "@/core/finance";

export const runtime = "nodejs";

// Liste des mois avec reste net + effet net du Kharja (lecture : admin + reader).
export async function GET() {
  return handle(async () => {
    await requireAuth();
    const months = await prisma.month.findMany({
      orderBy: { createdAt: "asc" },
      include: { expenses: { include: { category: true } }, kharja: { include: { lines: true } } },
    });
    const data = months.map((m) => ({
      id: m.id,
      label: m.label,
      clientPayment: m.clientPayment,
      remainder: monthNetRemainder(
        m.clientPayment,
        m.expenses.map((e) => ({ amount: e.amount, type: e.category.type })),
      ),
      kharja: m.kharja
        ? {
            id: m.kharja.id,
            net: m.kharja.lines.reduce((s, l) => s + (l.type === "IN" ? l.amount : -l.amount), 0),
          }
        : null,
    }));
    return json(data);
  });
}

// Création d'un mois (écriture : admin uniquement, vérifié serveur).
export async function POST(req: Request) {
  return handle(async () => {
    await requireAdmin();
    const body = createMonthSchema.parse(await req.json());
    const month = await prisma.month.create({ data: body });
    return json(month, 201);
  });
}
