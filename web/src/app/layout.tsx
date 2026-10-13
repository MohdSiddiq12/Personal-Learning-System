import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "LearnBook — read with intent",
  description:
    "A private reading desk that turns your books into page-cited ideas and actions.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}