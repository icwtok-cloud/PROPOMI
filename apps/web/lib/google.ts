// Etapa 2 (sección 6.2.1): carga puntual de Google Identity Services (GSI)
// para el botón de "Continuar con Google" del comprador, pedido recién en
// el último paso del wizard de oferta. Client ID no es secreto (viaja al
// navegador en cada uso de GSI de todos modos), por eso el default acá es
// seguro — se puede sobreescribir con NEXT_PUBLIC_GOOGLE_CLIENT_ID si el
// dueño del producto crea un client id distinto para producción.
export const GOOGLE_CLIENT_ID =
  process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID ||
  '872860769498-kmja44702diqc74d733ite8etttvkqp8.apps.googleusercontent.com';

declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (config: {client_id: string; callback: (resp: {credential: string}) => void}) => void;
          renderButton: (parent: HTMLElement, options: Record<string, unknown>) => void;
        };
      };
    };
  }
}

let scriptPromise: Promise<void> | null = null;

// Carga el script de GSI una sola vez por sesión de página, sin importar
// cuántas veces se monte el paso de verificación (evita <script> duplicados
// si el comprador vuelve atrás y adelante en el wizard).
export function loadGoogleScript(): Promise<void> {
  if (typeof window === 'undefined') return Promise.resolve();
  if (window.google?.accounts?.id) return Promise.resolve();
  if (scriptPromise) return scriptPromise;
  scriptPromise = new Promise((resolve, reject) => {
    const existing = document.getElementById('google-identity-script');
    if (existing) {
      existing.addEventListener('load', () => resolve());
      return;
    }
    const script = document.createElement('script');
    script.id = 'google-identity-script';
    script.src = 'https://accounts.google.com/gsi/client';
    script.async = true;
    script.defer = true;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error('No se pudo cargar Google Sign-In. Revisá tu conexión.'));
    document.head.appendChild(script);
  });
  return scriptPromise;
}

// Inicializa GSI y dibuja el botón dentro de `container`. `onToken` recibe
// el id_token (JWT) crudo — quien llama es responsable de mandarlo al
// backend (`linkGoogleIdentity` en lib/api.ts) para validarlo server-side;
// este helper nunca decide por sí mismo si el login es válido.
export async function renderGoogleButton(container: HTMLElement, onToken: (idToken: string) => void): Promise<void> {
  await loadGoogleScript();
  if (!window.google?.accounts?.id) throw new Error('Google Sign-In no está disponible.');
  window.google.accounts.id.initialize({
    client_id: GOOGLE_CLIENT_ID,
    callback: (resp) => onToken(resp.credential),
  });
  container.innerHTML = '';
  window.google.accounts.id.renderButton(container, {theme: 'outline', size: 'large', text: 'continue_with', width: 280});
}
