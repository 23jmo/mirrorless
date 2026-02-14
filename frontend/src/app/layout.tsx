import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Mirrorless",
  description: "AI-powered smart mirror for personalized outfit recommendations",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
