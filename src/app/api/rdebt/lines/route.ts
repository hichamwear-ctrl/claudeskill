import { prisma } from "@/lib/db";
import { requireAdmin, handle, json, HttpError } from "@/lib/http";
import { createRDebtLineSchema } from "@/lib/validation";
import { repaymentNet } from "@/core/finance";

export const runtime = "nodejs";

// Ajout d'une ligne au journal R. Le net (−8 % si virement) est calculé par la
// fonction pure et stocké. Écriture : admin uniquement.
export async function POST(req: Request) {
  return handle(async () => {
    await requireAdmin();
    const body = createRDebtLineSchema.parse(await req.json());

    const rdebt = await prisma.rDebt.findFirst();
    if (!rdebt) throw new HttpError(404, "Dette R non initialisée");

    const isRepayment = body.type === "REPAYMENT";
    const paymentMethod = isRepayment ? body.paymentMethod! : null;
    const amountNet =
      isRepayment && paymentMethod
        ? repaymentNet(body.amountGross, paymentMethod)
        : body.amountGross;

    const line = await prisma.rDebtLine.create({
      data: {
        rDebtId: rdebt.id,
        type: body.type,
        paymentMethod,
        amountGross: body.amountGross,
        amountNet,
      },
    });
    return json(line, 201);
  });
}
