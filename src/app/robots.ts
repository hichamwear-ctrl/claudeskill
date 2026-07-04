import type { MetadataRoute } from "next";

const base = process.env.AUTH_URL ?? "http://localhost:3000";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: "/",
      disallow: ["/client", "/barber", "/admin", "/api"],
    },
    sitemap: `${base}/sitemap.xml`,
  };
}
