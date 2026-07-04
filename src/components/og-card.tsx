import { ImageResponse } from "next/og";

export const OG_SIZE = { width: 1200, height: 630 };

/** Shared Open Graph / Twitter card renderer (Satori-safe styles). */
export function renderOgImage() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          padding: "80px",
          backgroundColor: "#0a0a0a",
          backgroundImage:
            "radial-gradient(circle at 25% 20%, rgba(212,175,55,0.22), transparent 45%)",
          color: "#fafafa",
          fontFamily: "sans-serif",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
          <div
            style={{
              width: 64,
              height: 64,
              borderRadius: 18,
              backgroundImage: "linear-gradient(135deg,#E8CE7B,#D4AF37,#B8942A)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "#0a0a0a",
              fontSize: 34,
              fontWeight: 800,
            }}
          >
            ✂
          </div>
          <span style={{ fontSize: 34, fontWeight: 700 }}>Barber Home</span>
        </div>
        <div
          style={{
            marginTop: 48,
            fontSize: 84,
            fontWeight: 800,
            lineHeight: 1.05,
            display: "flex",
            flexDirection: "column",
          }}
        >
          <span>Le barbershop</span>
          <span
            style={{
              backgroundImage: "linear-gradient(135deg,#E8CE7B,#D4AF37,#B8942A)",
              backgroundClip: "text",
              color: "transparent",
            }}
          >
            chez vous.
          </span>
        </div>
        <p style={{ marginTop: 36, fontSize: 30, color: "#a3a3a3" }}>
          Barber professionnel à domicile · Bruxelles · Noté 4,9/5
        </p>
      </div>
    ),
    OG_SIZE,
  );
}
