import type { Metadata } from "next";
import React from "react";

export const metadata: Metadata = {
  title: "AI Interview Video Player",
  description: "Interactive interview video player with transcript and subtitles",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body style={{ margin: 0, background: "#f4f6f9", fontFamily: "Arial, sans-serif" }}>
        {children}
      </body>
    </html>
  );
}
