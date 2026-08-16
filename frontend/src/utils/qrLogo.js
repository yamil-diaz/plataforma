// FASE 7.1: branding del QR con el logo oficial de Aeternum.
// Asset local reutilizado: frontend/public/favicon.svg (logo oficial, SVG,
// fondo transparente, autocontenido) servido por Vite en /favicon.svg.
// Sin URLs externas, sin almacenamiento, sin endpoints nuevos.

export const LOGO_URL = '/favicon.svg';

// El logo ocupa el 15 % del ancho del QR (rango exigido: 12 %–18 %).
export const QR_LOGO_RATIO = 0.15;

// Tope de seguridad: el logo nunca debe superar el 20 % del ancho.
export const QR_LOGO_MAX_RATIO = 0.20;

// Zona blanca de protección adicional a cada lado del logo.
export const QR_LOGO_PADDING_RATIO = 0.04;

export function computeLogoSize(qrSize) {
  return Math.round(qrSize * QR_LOGO_RATIO);
}

export function computeLogoZoneSize(qrSize) {
  const padding = Math.round(qrSize * QR_LOGO_PADDING_RATIO) * 2;
  return computeLogoSize(qrSize) + padding;
}