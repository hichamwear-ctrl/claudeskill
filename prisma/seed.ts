import { PrismaClient } from "@prisma/client";
import bcrypt from "bcryptjs";
import { SERVICE_LIST, SERVICES } from "../src/lib/pricing";

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

  // --- Barbers (approved & live) ---
  const barbersData = [
    {
      email: "karim@barberhome.be",
      firstName: "Karim",
      lastName: "El Amrani",
      level: "EXPERT" as const,
      yearsExperience: 9,
      instagram: "karim.cuts",
      bio: "Expert coupe & barbe, 9 ans d'expérience. Dégradés nets et soin de la barbe au rasoir.",
    },
    {
      email: "sofiane@barberhome.be",
      firstName: "Sofiane",
      lastName: "Benali",
      level: "CONFIRME" as const,
      yearsExperience: 5,
      instagram: "sofiane.barber",
      bio: "Barber confirmé, spécialiste des coupes tendance et du travail à la tondeuse.",
    },
  ];
  for (const b of barbersData) {
    const user = await prisma.user.upsert({
      where: { email: b.email },
      update: {},
      create: {
        email: b.email,
        firstName: b.firstName,
        lastName: b.lastName,
        phone: "+32 470 00 00 00",
        role: "BARBER",
        passwordHash,
      },
    });
    const barber = await prisma.barber.upsert({
      where: { userId: user.id },
      update: {
        bio: b.bio,
        level: b.level,
        yearsExperience: b.yearsExperience,
        instagram: b.instagram,
        approvalStatus: "APPROVED",
      },
      create: {
        userId: user.id,
        bio: b.bio,
        level: b.level,
        yearsExperience: b.yearsExperience,
        instagram: b.instagram,
        approvalStatus: "APPROVED",
        isAvailable: true,
        currentLat: 50.8467,
        currentLng: 4.3499,
      },
    });
    // A small portfolio (generated placeholders) so the profile isn't empty.
    const existingPhotos = await prisma.barberPhoto.count({
      where: { barberId: barber.id },
    });
    if (existingPhotos === 0) {
      await prisma.barberPhoto.createMany({
        data: [1, 2, 3].map((n) => ({
          barberId: barber.id,
          url: `https://picsum.photos/seed/${b.firstName.toLowerCase()}-${n}/600/600`,
          caption: `Réalisation ${n}`,
        })),
      });
    }
  }

  // --- A pending barber application (for the admin validation demo) ---
  const applicant = await prisma.user.upsert({
    where: { email: "yassine@barberhome.be" },
    update: {},
    create: {
      email: "yassine@barberhome.be",
      firstName: "Yassine",
      lastName: "Haddad",
      phone: "+32 471 22 33 44",
      role: "BARBER",
      passwordHash,
    },
  });
  await prisma.barber.upsert({
    where: { userId: applicant.id },
    update: {},
    create: {
      userId: applicant.id,
      bio: "Jeune barber motivé, formé en salon, cherche à se lancer à domicile.",
      level: "JUNIOR",
      yearsExperience: 2,
      instagram: "yassine.fades",
      approvalStatus: "PENDING",
      isAvailable: false,
    },
  });

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

  // --- Demo working hours + reservations (so every dashboard is populated) ---
  const karim = await prisma.user.findUnique({
    where: { email: "karim@barberhome.be" },
    include: { barberProfile: true },
  });
  const address = await prisma.address.findFirst({ where: { userId: client.id } });
  const barberId = karim?.barberProfile?.id;

  if (barberId) {
    for (let weekday = 1; weekday <= 5; weekday++) {
      await prisma.workingHours.upsert({
        where: { barberId_weekday: { barberId, weekday } },
        update: {},
        create: { barberId, weekday, startTime: "09:00", endTime: "18:00", enabled: true },
      });
    }
  }

  const alreadySeeded = await prisma.reservation.findFirst({
    where: { clientId: client.id },
  });

  if (!alreadySeeded && address && barberId) {
    const day = (offset: number) => {
      const d = new Date();
      d.setDate(d.getDate() + offset);
      d.setHours(14, 30, 0, 0);
      return d;
    };
    const person = (service: keyof typeof SERVICES) => ({
      type: SERVICES[service].type,
      service,
      price: SERVICES[service].price,
      duration: SERVICES[service].duration,
    });

    // Active reservation (barber assigned, upcoming)
    await prisma.reservation.create({
      data: {
        clientId: client.id,
        barberId,
        addressId: address.id,
        status: "BARBER_ATTRIBUE",
        scheduledAt: day(1),
        durationMinutes: SERVICES.ADULTE_COUPE_BARBE.duration,
        subtotal: 35,
        travelFee: 0,
        total: 35,
        persons: { create: [person("ADULTE_COUPE_BARBE")] },
        payment: { create: { method: "ON_SITE", amount: 35, status: "PENDING" } },
      },
    });

    // Completed reservation (paid + invoice + review + loyalty points)
    const done = await prisma.reservation.create({
      data: {
        clientId: client.id,
        barberId,
        addressId: address.id,
        status: "TERMINEE",
        scheduledAt: day(-4),
        durationMinutes: SERVICES.ADULTE_COUPE.duration,
        subtotal: 25,
        travelFee: 0,
        total: 25,
        persons: { create: [person("ADULTE_COUPE")] },
        payment: { create: { method: "ON_SITE", amount: 25, status: "PAID" } },
      },
    });
    await prisma.invoice.create({
      data: {
        number: `BH-${done.reference.slice(0, 8).toUpperCase()}`,
        reservationId: done.id,
        userId: client.id,
        amount: 25,
      },
    });
    await prisma.review.create({
      data: { reservationId: done.id, authorId: client.id, barberId, rating: 5, comment: "Barber au top, ponctuel et pro !" },
    });
    await prisma.loyaltyTransaction.create({
      data: { userId: client.id, points: 25, reason: `reservation:${done.id}` },
    });
    await prisma.user.update({
      where: { id: client.id },
      data: { loyaltyPoints: { increment: 25 } },
    });
    await prisma.barber.update({
      where: { id: barberId },
      data: { totalJobs: { increment: 1 } },
    });
  }

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
