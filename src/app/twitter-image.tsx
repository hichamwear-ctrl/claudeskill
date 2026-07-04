import { renderOgImage, OG_SIZE } from "@/components/og-card";

export const alt = "Barber Home — Le barber premium à domicile à Bruxelles";
export const size = OG_SIZE;
export const contentType = "image/png";

export default function Image() {
  return renderOgImage();
}
