import './globals.css';
import type { Metadata } from 'next';
import { AppProvider } from '@/lib/context';
import { Navbar } from '@/components/Navbar';
import { Footer } from '@/components/Footer';
import { CartDrawer } from '@/components/CartDrawer';
import { Toast } from '@/components/Toast';

export const metadata: Metadata = {
  title: 'Intelligent Payment & Order Platform',
  description: 'Production-grade e-commerce storefront and fintech operations dashboard with real-time fraud scoring.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="bg-slate-950 text-slate-100 min-h-screen flex flex-col antialiased selection:bg-emerald-500 selection:text-white">
        <AppProvider>
          <Navbar />
          <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
            {children}
          </main>
          <CartDrawer />
          <Toast />
          <Footer />
        </AppProvider>
      </body>
    </html>
  );
}
