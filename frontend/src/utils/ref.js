// Validación del parámetro ?ref= capturado por el QR de registro (FASE 3).
// Solo formato básico; la existencia/activación del código QR se validará
// en el backend en una fase posterior.
const REF_REGEX = /^[A-Za-z0-9_-]{1,32}$/;

export function sanitizeRef(raw) {
  if (typeof raw !== 'string' || raw.length === 0) return null;
  if (!REF_REGEX.test(raw)) return null;
  return raw;
}