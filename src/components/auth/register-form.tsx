"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { signIn } from "next-auth/react";
import { Loader2, User, Scissors } from "lucide-react";
import { registerSchema, type RegisterInput } from "@/lib/validations";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { useToast } from "@/components/ui/toast";
import { cn } from "@/lib/utils";

export function RegisterForm() {
  const router = useRouter();
  const { toast } = useToast();
  const {
    register,
    handleSubmit,
    watch,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<RegisterInput>({
    resolver: zodResolver(registerSchema),
    defaultValues: { role: "CLIENT" },
  });
  const role = watch("role");
  const isBarber = role === "BARBER";
  const [done, setDone] = useState(false);

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

    // Barber accounts are inactive until an admin validates them — no auto login.
    if (values.role === "BARBER") {
      setDone(true);
      toast({
        variant: "success",
        title: "Demande envoyée",
        description: "Votre compte barber sera activé après validation par l'équipe.",
      });
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

  if (done) {
    return (
      <div className="rounded-2xl border border-gold/30 bg-gold/5 p-6 text-center">
        <Scissors className="mx-auto size-8 text-gold" />
        <h2 className="mt-3 font-display text-lg font-bold">Demande enregistrée</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Votre dossier barber a été transmis à notre équipe. Vous recevrez un
          accès dès qu&apos;un administrateur l&apos;aura validé.
        </p>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      {/* Account type */}
      <div className="grid grid-cols-2 gap-3">
        <RoleCard
          active={!isBarber}
          icon={<User className="size-5" />}
          label="Client"
          hint="Réserver un barber"
          onClick={() => setValue("role", "CLIENT")}
        />
        <RoleCard
          active={isBarber}
          icon={<Scissors className="size-5" />}
          label="Barber"
          hint="Proposer mes services"
          onClick={() => setValue("role", "BARBER")}
        />
      </div>

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

      <Field
        label={isBarber ? "Téléphone" : "Téléphone (optionnel)"}
        error={errors.phone?.message}
      >
        <Input type="tel" placeholder="+32 4XX XX XX XX" {...register("phone")} />
      </Field>

      {isBarber && (
        <div className="space-y-4 rounded-2xl border border-border bg-card/50 p-4">
          <p className="text-xs font-semibold uppercase tracking-wider text-gold">
            Dossier barber
          </p>
          <Field
            label="Instagram / Snapchat"
            error={errors.social?.message}
          >
            <Input placeholder="@moncompte" {...register("social")} />
          </Field>
          <div className="grid grid-cols-2 gap-3">
            <Field
              label="Années d'expérience"
              error={errors.yearsExperience?.message}
            >
              <Input
                type="number"
                min={0}
                placeholder="5"
                {...register("yearsExperience")}
              />
            </Field>
            <Field label="Niveau" error={errors.level?.message}>
              <select
                className="flex h-11 w-full rounded-xl border border-input bg-secondary/50 px-4 text-sm focus-visible:border-gold/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gold/20"
                defaultValue=""
                {...register("level")}
              >
                <option value="" disabled>
                  Choisir…
                </option>
                <option value="JUNIOR">Junior</option>
                <option value="CONFIRME">Confirmé</option>
                <option value="EXPERT">Expert</option>
              </select>
            </Field>
          </div>
          <Field label="Biographie" error={errors.bio?.message}>
            <Textarea
              placeholder="Présentez votre parcours, vos spécialités…"
              {...register("bio")}
            />
          </Field>
        </div>
      )}

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
        {isBarber ? "Envoyer ma demande" : "Créer mon compte"}
      </Button>
    </form>
  );
}

function RoleCard({
  active,
  icon,
  label,
  hint,
  onClick,
}: {
  active: boolean;
  icon: React.ReactNode;
  label: string;
  hint: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "flex flex-col items-start gap-1 rounded-xl border p-3 text-left transition-colors",
        active
          ? "border-gold bg-gold/10 text-gold"
          : "border-border hover:border-gold/40",
      )}
    >
      {icon}
      <span className="text-sm font-semibold text-foreground">{label}</span>
      <span className="text-xs text-muted-foreground">{hint}</span>
    </button>
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
