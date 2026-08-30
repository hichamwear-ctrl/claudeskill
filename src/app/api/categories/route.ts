import { prisma } from "@/lib/db";
import { requireAdmin, requireAuth, handle, json } from "@/lib/http";
import { createCategorySchema } from "@/lib/validation";

export const runtime = "nodejs";

// Grille de catégories visibles (hors internes TVA). Lecture : admin + reader.
export async function GET() {
  return handle(async () => {
    await requireAuth();
    const categories = await prisma.category.findMany({
      where: { isSystem: false },
      orderBy: [{ type: "asc" }, { name: "asc" }],
    });
    return json(categories);
  });
}

// Création d'une catégorie personnalisée (§3.3). Écriture : admin uniquement.
export async function POST(req: Request) {
  return handle(async () => {
    await requireAdmin();
    const body = createCategorySchema.parse(await req.json());
    const category = await prisma.category.create({
      data: { ...body, isCustom: true, isSystem: false },
    });
    return json(category, 201);
  });
}
