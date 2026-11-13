import type { Metadata } from 'next';
import './globals.css';
export const metadata: Metadata = { title: 'ID Card Studio', description: 'Local school and college ID card production' };
export default function RootLayout({ children }: {
    children: React.ReactNode;
}) { return <html lang="en"><body>{children}</body></html>; }
