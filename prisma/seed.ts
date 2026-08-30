import { PrismaClient } from "@prisma/client";
import { hash } from "@node-rs/argon2";
import { DEFAULT_CATEGORIES } from "../src/lib/categories";

const prisma = new PrismaClient();

// Seed obligatoire de la dette R : 23 367,50 € = 2 336 750 centimes.
const R_DEBT_SEED_CENTS = 2_336_750;

function requireEnv(name: string): string {
  const v = process.env[name];
  if (!v) throw new Error(`Variable d'environnement manquante : ${name}`);
  return v;
}

async function main() {
  // 1) Catégories (système + par défaut), idempotent.
  for (const c of DEFAULT_CATEGORIES) {
    if (c.id) {
      await prisma.category.upsert({
        where: { id: c.id },
        update: { name: c.name, icon: c.icon, type: c.type, isSystem: c.isSystem ?? false },
        create: {
          id: c.id,
          name: c.name,
          icon: c.icon,
          type: c.type,
          isSystem: c.isSystem ?? false,
          isCustom: false,
        },
      });
    } else {
      const existing = await prisma.category.findFirst({
        where: { name: c.name, isCustom: false },
      });
      if (!existing) {
        await prisma.category.create({
          data: { name: c.name, icon: c.icon, type: c.type, isCustom: false, isSystem: false },
        });
      }
    }
  }

  // 2) Dette R : une seule ligne de base, seed initial obligatoire.
  const rdebt = await prisma.rDebt.findFirst();
  if (!rdebt) {
    await prisma.rDebt.create({ data: { baseAmount: R_DEBT_SEED_CENTS } });
  }

  // 3) Comptes initiaux (mots de passe depuis l'environnement, jamais en dur).
  const adminEmail = requireEnv("SEED_ADMIN_EMAIL");
  const adminPassword = requireEnv("SEED_ADMIN_PASSWORD");
  const readerEmail = requireEnv("SEED_READER_EMAIL");
  const readerPassword = requireEnv("SEED_READER_PASSWORD");

  await prisma.user.upsert({
    where: { email: adminEmail },
    update: {},
    create: { email: adminEmail, passwordHash: await hash(adminPassword), role: "ADMIN" },
  });
  await prisma.user.upsert({
    where: { email: readerEmail },
    update: {},
    create: { email: readerEmail, passwordHash: await hash(readerPassword), role: "READER" },
  });
}

main()
  .then(() => prisma.$disconnect())
  .catch(async (e) => {
    console.error(e);
    await prisma.$disconnect();
    process.exit(1);
  });
