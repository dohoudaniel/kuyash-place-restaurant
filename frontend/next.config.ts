import type { NextConfig } from "next";

const apiUrl = new URL(process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1");

const nextConfig: NextConfig = {
  images: {
    // Next 16 refuses to optimise images from local/private IPs. Django serves
    // uploads from localhost in development, so allow it there and nowhere else —
    // `next build` runs with NODE_ENV=production, so this is never on in a deploy.
    dangerouslyAllowLocalIP: process.env.NODE_ENV === "development",
    remotePatterns: [
      // Production: menu and gallery photos from Supabase Storage's public path.
      {
        protocol: "https",
        hostname: "**.supabase.co",
        pathname: "/storage/v1/object/public/**",
      },
      // Development: Django serves uploads from /media/ on the API origin.
      {
        protocol: apiUrl.protocol === "https:" ? "https" : "http",
        hostname: apiUrl.hostname,
        port: apiUrl.port,
        pathname: "/media/**",
      },
    ],
  },
};

export default nextConfig;
