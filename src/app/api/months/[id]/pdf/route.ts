import { requireAuth, handle, HttpError } from "@/lib/http";
import { renderMonthPdf } from "@/lib/month-pdf";

export const runtime = "nodejs";

type Ctx = { params: Promise<{ id: string }> };

// Génération PDF du mois. Lecture : admin ET reader (R en lecture seule).
export async function GET(_req: Request, { params }: Ctx) {
  return handle(async () => {
    await requireAuth();
    const { id } = await params;
    const buffer = await renderMonthPdf(id);
    if (!buffer) throw new HttpError(404, "Mois introuvable");
    return new Response(new Uint8Array(buffer), {
      status: 200,
      headers: {
        "Content-Type": "application/pdf",
        "Content-Disposition": `inline; filename="mois-${id}.pdf"`,
      },
    });
  });
}
