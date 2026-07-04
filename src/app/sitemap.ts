import type { MetadataRoute } from "next";

const base = process.env.AUTH_URL ?? "http://localhost:3000";

export default function sitemap(): MetadataRoute.Sitemap {
  const now = new Date();
  return [
    { url: base, lastModified: now, changeFrequency: "weekly", priority: 1 },
    { url: `${base}/login`, lastModified: now, priority: 0.5 },
    { url: `${base}/register`, lastModified: now, priority: 0.8 },
  ];
}
