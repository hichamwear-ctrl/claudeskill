"use client";

import { motion } from "framer-motion";
import { Home, Scissors } from "lucide-react";
import { projectPoints } from "@/lib/geo-project";
import { cn } from "@/lib/utils";
import type { TrackingMapProps } from "@/components/map/types";

const W = 400;
const H = 260;

/**
 * Self-contained tracking map (default provider): renders the client and
 * barber positions plus the route between them in an SVG — no external tiles,
 * no API key, no network. A Leaflet/Google provider can replace it behind the
 * same props (see map/types.ts).
 */
export function SvgTrackingMap({ client, barber, className }: TrackingMapProps) {
  const points = [
    client ? { ...client, kind: "client" as const } : null,
    barber ? { ...barber, kind: "barber" as const } : null,
  ].filter(Boolean) as Array<{ lat: number; lng: number; kind: "client" | "barber" }>;

  const projected = projectPoints(points, W, H);
  const byKind = Object.fromEntries(points.map((p, i) => [p.kind, projected[i]]));

  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-2xl border border-border bg-secondary/30",
        className,
      )}
    >
      <svg viewBox={`0 0 ${W} ${H}`} className="h-full w-full" role="img"
        aria-label="Carte de suivi du barber">
        {/* subtle grid */}
        <defs>
          <pattern id="grid" width="32" height="32" patternUnits="userSpaceOnUse">
            <path d="M32 0H0V32" fill="none" stroke="rgba(255,255,255,0.04)" strokeWidth="1" />
          </pattern>
          <linearGradient id="route" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0" stopColor="#B8942A" />
            <stop offset="1" stopColor="#E8CE7B" />
          </linearGradient>
        </defs>
        <rect width={W} height={H} fill="url(#grid)" />

        {byKind.client && byKind.barber && (
          <line
            x1={byKind.barber.x}
            y1={byKind.barber.y}
            x2={byKind.client.x}
            y2={byKind.client.y}
            stroke="url(#route)"
            strokeWidth="3"
            strokeDasharray="7 6"
            strokeLinecap="round"
          />
        )}

        {byKind.client && (
          <MapPin x={byKind.client.x} y={byKind.client.y} color="#22c55e" />
        )}
        {byKind.barber && (
          <motion.g
            initial={false}
            animate={{ x: byKind.barber.x, y: byKind.barber.y }}
            transition={{ type: "spring", damping: 24, stiffness: 120 }}
          >
            <MapPin x={0} y={0} color="#D4AF37" pulse />
          </motion.g>
        )}
      </svg>

      {/* legend */}
      <div className="absolute bottom-3 left-3 flex gap-3 text-xs">
        <span className="flex items-center gap-1.5 text-emerald-400">
          <Home className="size-3.5" /> Vous
        </span>
        <span className="flex items-center gap-1.5 text-gold">
          <Scissors className="size-3.5" /> Barber
        </span>
      </div>
    </div>
  );
}

function MapPin({
  x,
  y,
  color,
  pulse = false,
}: {
  x: number;
  y: number;
  color: string;
  pulse?: boolean;
}) {
  return (
    <g transform={`translate(${x} ${y})`}>
      {pulse && (
        <circle r="12" fill={color} opacity="0.25">
          <animate attributeName="r" from="8" to="20" dur="1.6s" repeatCount="indefinite" />
          <animate attributeName="opacity" from="0.35" to="0" dur="1.6s" repeatCount="indefinite" />
        </circle>
      )}
      <circle r="7" fill={color} stroke="#0a0a0a" strokeWidth="2" />
    </g>
  );
}
