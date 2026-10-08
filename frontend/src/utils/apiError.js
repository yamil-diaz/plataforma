export function formatApiError(err, fallback = 'Ocurrió un error. Inténtalo de nuevo.') {
  const detail = err?.response?.data?.detail;
  if (!detail) {
    if (err?.code === 'ERR_NETWORK' || err?.message?.includes('Network')) {
      return 'Sin conexión con el servidor. Revisa tu red.';
    }
    return fallback;
  }
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (!item) return '';
        if (typeof item === 'string') return item;
        const field = Array.isArray(item.loc) ? item.loc.filter((p) => p !== 'body').join('.') : '';
        const msg = item.msg || 'dato inválido';
        return field ? `${field}: ${msg}` : msg;
      })
      .filter(Boolean)
      .join(' · ');
  }
  if (typeof detail === 'object') {
    return detail.msg || detail.message || fallback;
  }
  return fallback;
}
