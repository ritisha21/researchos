import type { Metadata } from 'next';
import './globals.css';
import { Toaster } from 'react-hot-toast';
import { Navbar } from '@/components/layout/Navbar';

export const metadata: Metadata = {
  title: 'ResearchOS — AI Research Platform',
  description: 'AI-powered research learning platform. Navigate papers, generate roadmaps, chat with research.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen">
        <Navbar />
        <main className="min-h-[calc(100vh-4rem)]">
          {children}
        </main>
        <Toaster
          position="bottom-right"
          toastOptions={{
            style: {
              background: 'hsl(222 47% 11%)',
              color: 'hsl(213 31% 91%)',
              border: '1px solid hsl(216 34% 17%)',
              borderRadius: '0.75rem',
              fontSize: '0.875rem',
            },
          }}
        />
      </body>
    </html>
  );
}
