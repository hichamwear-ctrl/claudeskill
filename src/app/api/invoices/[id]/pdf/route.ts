import { auth } from "@/server/auth";
import { prisma } from "@/server/prisma";
import { fail } from "@/server/api";
import { generateInvoicePdf } from "@/server/invoice-pdf";

/** Real PDF invoice (pdf-lib). RBAC: owner client or admin. */
export async function GET(
  _req: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const session = await auth();
  if (!session?.user) return fail("Non authentifié", 401);

  const { id } = await params;
  const reservation = await prisma.reservation.findUnique({
    where: { id },
    select: { clientId: true, reference: true },
  });
  if (!reservation) return fail("Introuvable", 404);
  if (reservation.clientId !== session.user.id && session.user.role !== "ADMIN")
    return fail("Accès refusé", 403);

  const bytes = await generateInvoicePdf(id);
  if (!bytes) return fail("Introuvable", 404);

  const number = `BH-${reservation.reference.slice(0, 8).toUpperCase()}`;
  return new Response(Buffer.from(bytes), {
    headers: {
      "Content-Type": "application/pdf",
      "Content-Disposition": `inline; filename="${number}.pdf"`,
    },
  });
}
