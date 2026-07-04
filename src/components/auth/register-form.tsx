"use client";

import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { signIn } from "next-auth/react";
import { Loader2 } from "lucide-react";
import { registerSchema, type RegisterInput } from "@/lib/validations";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useToast } from "@/components/ui/toast";

export function RegisterForm() {
  const router = useRouter();
  const { toast } = useToast();
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<RegisterInput>({ resolver: zodResolver(registerSchema) });

  async function onSubmit(values: RegisterInput) {
    const res = await fetch("/api/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(values),
    });

    if (!res.ok) {
      const { error } = await res.json().catch(() => ({ error: "Erreur" }));
      toast({ variant: "error", title: "Inscription échouée", description: error });
      return;
    }

    await signIn("credentials", {
      email: values.email,
      password: values.password,
      redirect: false,
    });
    toast({ variant: "success", title: "Bienvenue chez Barber Home !" });
    router.push("/client");
    router.refresh();
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <div className="grid grid-cols-2 gap-3">
        <Field label="Prénom" error={errors.firstName?.message}>
          <Input placeholder="Jean" {...register("firstName")} />
        </Field>
        <Field label="Nom" error={errors.lastName?.message}>
          <Input placeholder="Dupont" {...register("lastName")} />
        </Field>
      </div>

      <Field label="Pseudo (optionnel)" error={errors.username?.message}>
        <Input placeholder="jeand" {...register("username")} />
      </Field>

      <Field label="Email" error={errors.email?.message}>
        <Input type="email" placeholder="vous@exemple.com" {...register("email")} />
      </Field>

      <Field label="Téléphone (optionnel)" error={errors.phone?.message}>
        <Input type="tel" placeholder="+32 4XX XX XX XX" {...register("phone")} />
      </Field>

      <div className="grid grid-cols-2 gap-3">
        <Field label="Mot de passe" error={errors.password?.message}>
          <Input type="password" placeholder="••••••••" {...register("password")} />
        </Field>
        <Field label="Confirmer" error={errors.confirmPassword?.message}>
          <Input
            type="password"
            placeholder="••••••••"
            {...register("confirmPassword")}
          />
        </Field>
      </div>

      <Button type="submit" className="w-full" disabled={isSubmitting}>
        {isSubmitting && <Loader2 className="size-4 animate-spin" />}
        Créer mon compte
      </Button>
    </form>
  );
}

function Field({
  label,
  error,
  children,
}: {
  label: string;
  error?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-1.5">
      <Label>{label}</Label>
      {children}
      {error && <p className="text-xs text-rose-400">{error}</p>}
    </div>
  );
}
