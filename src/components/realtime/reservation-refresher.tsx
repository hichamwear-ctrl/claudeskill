"use client";

/**
 * Replaces the Phase 1/2 polling `AutoRefresh`: subscribes to each active
 * reservation's realtime channel and revalidates server data the instant a
 * status event arrives — no interval polling. Inert without Supabase env.
 */
import { useRouter } from "next/navigation";
import { useReservationChannel } from "@/hooks/useReservationChannel";

function ChannelWatcher({ id }: { id: string }) {
  const router = useRouter();
  useReservationChannel(id, () => router.refresh());
  return null;
}

export function ReservationRefresher({ ids }: { ids: string[] }) {
  return (
    <>
      {ids.map((id) => (
        <ChannelWatcher key={id} id={id} />
      ))}
    </>
  );
}
