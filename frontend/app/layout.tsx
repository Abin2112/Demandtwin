import type { Metadata } from "next";
import "./style.css";

export const metadata: Metadata = {
  title: "DemandTwin | Market research workspace",
  description: "Design consumer experiments and simulate product choices with traceable evidence.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en" suppressHydrationWarning><body>{children}</body></html>;
}
