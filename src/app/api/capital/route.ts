import { requireAuth, handle, json } from "@/lib/http";
import { computeGlobalCapital, computeCapitalBreakdown } from "@/lib/finance-queries";

export const runtime = "nodejs";

// Capital global + décomposition mois par mois (pour la vue "Détail").
export async function GET() {
  return handle(async () => {
    await requireAuth();
    const [total, breakdown] = await Promise.all([
      computeGlobalCapital(),
      computeCapitalBreakdown(),
    ]);
    return json({ total, breakdown });
  });
}
