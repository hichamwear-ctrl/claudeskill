/**
 * Central image registry (Phase 2).
 *
 * Every visual references a semantic key here — swapping the artwork for real
 * barbershop photography is a one-file edit: drop files in `public/images/`
 * and point the key at the new path (e.g. "/images/hero.jpg"). The <Media>
 * component renders local SVG placeholders and real rasters transparently.
 */
export interface SiteImage {
  src: string;
  alt: string;
  /** intrinsic ratio, width / height — used to reserve layout space (no CLS) */
  ratio: number;
}

export const SITE_IMAGES = {
  heroPortrait: {
    src: "/images/barber-portrait.svg",
    alt: "Barber professionnel en pleine prestation à domicile",
    ratio: 3 / 4,
  },
  shopScene: {
    src: "/images/barbershop-scene.svg",
    alt: "Ambiance barbershop premium, tons sombres et dorés",
    ratio: 4 / 3,
  },
  grooming: {
    src: "/images/grooming.svg",
    alt: "Coupe et taille de barbe soignées",
    ratio: 1,
  },
  texture: {
    src: "/images/texture.svg",
    alt: "",
    ratio: 16 / 9,
  },
} satisfies Record<string, SiteImage>;

export type SiteImageKey = keyof typeof SITE_IMAGES;

export function getImage(key: SiteImageKey): SiteImage {
  return SITE_IMAGES[key];
}
