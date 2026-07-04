import Image from "next/image";
import { getImage, type SiteImageKey } from "@/lib/site-images";
import { cn } from "@/lib/utils";

/**
 * Renders a registry image inside a ratio-locked, rounded frame (no layout
 * shift). SVG placeholders load via a native lazy <img>; real rasters go
 * through next/image for optimization. Swapping art never touches call sites.
 */
export function Media({
  image,
  className,
  priority = false,
  rounded = "rounded-2xl",
}: {
  image: SiteImageKey;
  className?: string;
  priority?: boolean;
  rounded?: string;
}) {
  const { src, alt, ratio } = getImage(image);
  const isVector = src.endsWith(".svg");

  return (
    <div
      className={cn("relative overflow-hidden bg-secondary/40", rounded, className)}
      style={{ aspectRatio: String(ratio) }}
    >
      {isVector ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={src}
          alt={alt}
          loading={priority ? "eager" : "lazy"}
          decoding="async"
          className="absolute inset-0 h-full w-full object-cover"
        />
      ) : (
        <Image
          src={src}
          alt={alt}
          fill
          sizes="(max-width: 768px) 100vw, 50vw"
          priority={priority}
          className="object-cover"
        />
      )}
    </div>
  );
}
