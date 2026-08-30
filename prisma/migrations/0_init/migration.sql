-- CreateSchema
CREATE SCHEMA IF NOT EXISTS "public";

-- CreateEnum
CREATE TYPE "Role" AS ENUM ('ADMIN', 'READER');

-- CreateEnum
CREATE TYPE "CategoryType" AS ENUM ('SUBTRACTION', 'ADDITION');

-- CreateEnum
CREATE TYPE "KharjaType" AS ENUM ('IN', 'OUT');

-- CreateEnum
CREATE TYPE "RDebtType" AS ENUM ('INCREASE', 'REPAYMENT');

-- CreateEnum
CREATE TYPE "PaymentMethod" AS ENUM ('CASH', 'TRANSFER');

-- CreateTable
CREATE TABLE "User" (
    "id" TEXT NOT NULL,
    "email" TEXT NOT NULL,
    "passwordHash" TEXT NOT NULL,
    "role" "Role" NOT NULL,
    "failedLogins" INTEGER NOT NULL DEFAULT 0,
    "lockedUntil" TIMESTAMP(3),
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "User_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Month" (
    "id" TEXT NOT NULL,
    "label" TEXT NOT NULL,
    "clientPayment" INTEGER NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "Month_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Category" (
    "id" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "icon" TEXT NOT NULL,
    "type" "CategoryType" NOT NULL,
    "isCustom" BOOLEAN NOT NULL DEFAULT false,
    "isSystem" BOOLEAN NOT NULL DEFAULT false,

    CONSTRAINT "Category_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "ExpenseLine" (
    "id" TEXT NOT NULL,
    "monthId" TEXT NOT NULL,
    "categoryId" TEXT NOT NULL,
    "amount" INTEGER NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "ExpenseLine_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Kharja" (
    "id" TEXT NOT NULL,
    "monthId" TEXT NOT NULL,

    CONSTRAINT "Kharja_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "KharjaLine" (
    "id" TEXT NOT NULL,
    "kharjaId" TEXT NOT NULL,
    "type" "KharjaType" NOT NULL,
    "amount" INTEGER NOT NULL,
    "note" TEXT NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "KharjaLine_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "RDebt" (
    "id" TEXT NOT NULL,
    "baseAmount" INTEGER NOT NULL,

    CONSTRAINT "RDebt_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "RDebtLine" (
    "id" TEXT NOT NULL,
    "rDebtId" TEXT NOT NULL,
    "type" "RDebtType" NOT NULL,
    "paymentMethod" "PaymentMethod",
    "amountGross" INTEGER NOT NULL,
    "amountNet" INTEGER NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "RDebtLine_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "User_email_key" ON "User"("email");

-- CreateIndex
CREATE INDEX "Month_createdAt_idx" ON "Month"("createdAt");

-- CreateIndex
CREATE INDEX "ExpenseLine_monthId_idx" ON "ExpenseLine"("monthId");

-- CreateIndex
CREATE UNIQUE INDEX "Kharja_monthId_key" ON "Kharja"("monthId");

-- CreateIndex
CREATE INDEX "KharjaLine_kharjaId_idx" ON "KharjaLine"("kharjaId");

-- CreateIndex
CREATE INDEX "RDebtLine_rDebtId_idx" ON "RDebtLine"("rDebtId");

-- AddForeignKey
ALTER TABLE "ExpenseLine" ADD CONSTRAINT "ExpenseLine_monthId_fkey" FOREIGN KEY ("monthId") REFERENCES "Month"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "ExpenseLine" ADD CONSTRAINT "ExpenseLine_categoryId_fkey" FOREIGN KEY ("categoryId") REFERENCES "Category"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Kharja" ADD CONSTRAINT "Kharja_monthId_fkey" FOREIGN KEY ("monthId") REFERENCES "Month"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "KharjaLine" ADD CONSTRAINT "KharjaLine_kharjaId_fkey" FOREIGN KEY ("kharjaId") REFERENCES "Kharja"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "RDebtLine" ADD CONSTRAINT "RDebtLine_rDebtId_fkey" FOREIGN KEY ("rDebtId") REFERENCES "RDebt"("id") ON DELETE CASCADE ON UPDATE CASCADE;

