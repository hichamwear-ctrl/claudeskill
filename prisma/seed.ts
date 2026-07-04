import { PrismaClient } from "@prisma/client";
import bcrypt from "bcryptjs";
import { SERVICE_LIST } from "../src/lib/pricing";

const prisma = new PrismaClient();

async function main() {
  console.log("🌱 Seeding Barber Home…");

  const passwordHash = await bcrypt.hash("password123", 12);

  // --- Services catalogue ---
  for (const s of SERVICE_LIST) {
    await prisma.service.upsert({
      where: { key: s.key },
      update: { name: s.name, price: s.price, duration: s.duration, type: s.type },
      create: {
        key: s.key,
        name: s.name,
        price: s.price,
        duration: s.duration,
        type: s.type,
      },
    });
  }

  // --- Admin ---
  await prisma.user.upsert({
    where: { email: "admin@barberhome.be" },
    update: {},
    create: {
      email: "admin@barberhome.be",
      firstName: "Admin",
      lastName: "Barber Home",
      username: "admin",
      role: "ADMIN",
      passwordHash,
    },
  });

  // --- Barbers ---
  const barbersData = [
    { email: "karim@barberhome.be", firstName: "Karim", lastName: "El Amrani" },
    { email: "sofiane@barberhome.be", firstName: "Sofiane", lastName: "Benali" },
  ];
  for (const b of barbersData) {
    const user = await prisma.user.upsert({
      where: { email: b.email },
      update: {},
      create: {
        email: b.email,
        firstName: b.firstName,
        lastName: b.lastName,
        role: "BARBER",
        passwordHash,
      },
    });
    await prisma.barber.upsert({
      where: { userId: user.id },
      update: {},
      create: {
        userId: user.id,
        bio: "Barber professionnel spécialisé coupe & barbe.",
        isAvailable: true,
        currentLat: 50.8467,
        currentLng: 4.3499,
      },
    });
  }

  // --- Client with an address ---
  const client = await prisma.user.upsert({
    where: { email: "client@barberhome.be" },
    update: {},
    create: {
      email: "client@barberhome.be",
      firstName: "Julien",
      lastName: "Martin",
      username: "julien",
      phone: "+32 470 12 34 56",
      role: "CLIENT",
      passwordHash,
    },
  });

  const existingAddress = await prisma.address.findFirst({
    where: { userId: client.id },
  });
  if (!existingAddress) {
    await prisma.address.create({
      data: {
        userId: client.id,
        label: "Domicile",
        street: "Avenue Louise",
        number: "143",
        city: "Bruxelles",
        postalCode: "1050",
        country: "Belgique",
        latitude: 50.827,
        longitude: 4.363,
        insideZone: true,
        isDefault: true,
      },
    });
  }

  // --- Promo codes ---
  await prisma.promoCode.upsert({
    where: { code: "WELCOME10" },
    update: {},
    create: {
      code: "WELCOME10",
      description: "10% de réduction sur votre première réservation",
      percentOff: 10,
      active: true,
      maxUses: 1000,
    },
  });
  await prisma.promoCode.upsert({
    where: { code: "BARBER5" },
    update: {},
    create: {
      code: "BARBER5",
      description: "5 € offerts",
      amountOff: 5,
      active: true,
    },
  });

  console.log("✅ Seed terminé.");
  console.log("   Admin  : admin@barberhome.be  / password123");
  console.log("   Barber : karim@barberhome.be  / password123");
  console.log("   Client : client@barberhome.be / password123");
}

main()
  .catch((e) => {
    console.error(e);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
