import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "PrepMate",
  description:
    "Personal AI interview coach using your resume, target role, and job description.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
