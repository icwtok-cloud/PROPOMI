import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Propomi — Descubrí, decidí, negociá',
  description: 'La capa de intención y decisión inmobiliaria para LATAM.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body>{children}</body>
    </html>
  );
}
