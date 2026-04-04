/** @type {import('next').NextConfig} */
const nextConfig = {
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || "https://q3vgjfnybq.ap-south-1.awsapprunner.com",
  },
};

export default nextConfig;
