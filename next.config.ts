import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    // Only proxy to localhost in development
    // In production, use NEXT_PUBLIC_API_URL environment variable
    const apiUrl = process.env.NEXT_PUBLIC_API_URL;
    
    if (process.env.NODE_ENV === 'development' && !apiUrl) {
      return [
        {
          source: '/api/:path*',
          destination: 'http://localhost:8000/:path*',
        },
      ];
    }
    
    // In production, don't use rewrites - use the API URL directly
    return [];
  },
};

export default nextConfig;
