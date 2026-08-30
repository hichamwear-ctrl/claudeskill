import { redirect } from "next/navigation";
import { auth } from "@/lib/auth";
import { Providers } from "@/components/Providers";
import { BottomNav } from "@/components/BottomNav";

// Garde serveur : pas de session -> redirection login. Défense en profondeur
// (l'API reste l'autorité sur les rôles).
export default async function AppLayout({ children }: { children: React.ReactNode }) {
  const session = await auth();
  if (!session?.user) redirect("/login");

  return (
    <Providers>
      <div className="shell">
        {children}
        <BottomNav />
      </div>
    </Providers>
  );
}
