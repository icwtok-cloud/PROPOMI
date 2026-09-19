import { NextRequest, NextResponse } from 'next/server';

// Etapa 015 (subdominios por agencia). El dominio raíz es configurable por
// env (`NEXT_PUBLIC_ROOT_DOMAIN`) para no hardcodear 'propomi.lat' — en
// local/preview puede no existir todavía. La infra real (registro wildcard
// `*.propomi.lat` en el proveedor de DNS + agregar el wildcard domain en
// Vercel) queda fuera de este archivo: eso lo arma el dueño del producto en
// esos paneles, este middleware solo resuelve el request una vez que ya
// llegó a Next.js con ese host.
const ROOT_DOMAIN = process.env.NEXT_PUBLIC_ROOT_DOMAIN || 'propomi.lat';

// Hosts que nunca se tratan como subdominio de agencia, aunque el string
// tenga puntos: el dominio raíz (con o sin www), el deploy default de
// Vercel (sin subdominios de agencia reales todavía) y localhost en dev.
const EXCLUDED_HOSTS = new Set([
  ROOT_DOMAIN,
  `www.${ROOT_DOMAIN}`,
  'propomi.vercel.app',
  'localhost:3000',
  'localhost',
]);

export function middleware(req: NextRequest) {
  const host = (req.headers.get('host') || '').toLowerCase();

  if (EXCLUDED_HOSTS.has(host) || host.endsWith('.vercel.app')) {
    return NextResponse.next();
  }
  if (!host.endsWith(`.${ROOT_DOMAIN}`)) {
    // Host desconocido (dominio propio sin configurar, IP, etc.): no
    // romper el request — dejar pasar como si fuera la home normal.
    return NextResponse.next();
  }

  const slug = host.slice(0, host.length - ROOT_DOMAIN.length - 1);
  if (!slug || slug === 'www' || req.nextUrl.pathname !== '/') {
    // Solo se reescribe la home ('/'). Cualquier otra ruta pedida contra un
    // subdominio de agencia (ej. /agencia, /admin) sigue funcionando normal
    // en vez de heredar el rewrite y romperse.
    return NextResponse.next();
  }

  const url = req.nextUrl.clone();
  url.pathname = `/tienda/${slug}`;
  return NextResponse.rewrite(url);
}

export const config = {
  // No interceptar assets estáticos ni rutas internas de Next.
  matcher: ['/((?!_next|favicon.ico).*)'],
};
