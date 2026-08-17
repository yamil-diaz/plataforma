"""Observabilidad interna de la IA de Aeternum (FASE 8.9).

Métricas ligeras EN MEMORIA, por proceso/instancia. Se pierden al reiniciar
el proceso (a propósito: NO hay persistencia en BD ni en archivo).

Semántica (una "operación lógica" = una solicitud que llama al proveedor):
  - total_calls:           operaciones lógicas iniciadas (el reintento NO
                           cuenta aquí: es parte de la misma operación).
  - provider_calls:        llamadas reales al proveedor (intentos). Un retry
                           suma aquí, no en total_calls.
  - successful_calls:      operaciones que terminaron con éxito.
  - failed_calls:          operaciones que terminaron sin éxito tras llamar
                           al proveedor (timeout final, no disponible final,
                           error no transitorio, excepción inesperada,
                           respuesta inválida definitiva).
  - retry_count:           reintentos ejecutados (máx 1 por operación).
  - transient_failures:    fallos transitorios observados (timeout o error
                           reintentable).
  - permanent_failures:    fallos definitivos NO reintentables (error no
                           transitorio, excepción inesperada, respuesta
                           inválida no reintentable).
  - timeout_count:         timeouts observados.
  - total_duration_ms:     suma de duraciones de operaciones (éxito y fallo).

Thread-safety: todos los incrementos y lecturas ocurren bajo un lock único.
snapshot() devuelve una copia numérica. Sin dependencias externas.

SEGURIDAD: las métricas solo contienen números. NUNCA contienen prompts,
respuestas, contenido de libros, JWT, cookies, contraseñas, API keys ni
secretos. No se exponen a usuarios: no existe endpoint público (FASE 8.9).
"""

import threading


class AIMetrics:
    """Contadores internos de observabilidad de IA (en memoria)."""

    def __init__(self):
        self._lock = threading.Lock()
        self._reset_locked()

    def _reset_locked(self):
        self.total_calls = 0
        self.provider_calls = 0
        self.successful_calls = 0
        self.failed_calls = 0
        self.retry_count = 0
        self.transient_failures = 0
        self.permanent_failures = 0
        self.timeout_count = 0
        self.total_duration_ms = 0

    def reset(self):
        """Reinicia todos los contadores (tests o reinicio de proceso)."""
        with self._lock:
            self._reset_locked()

    def record_call_start(self):
        with self._lock:
            self.total_calls += 1

    def record_provider_call(self):
        with self._lock:
            self.provider_calls += 1

    def record_success(self, duration_ms):
        with self._lock:
            self.successful_calls += 1
            self.total_duration_ms += max(duration_ms, 0)

    def record_failure(self, duration_ms):
        with self._lock:
            self.failed_calls += 1
            self.total_duration_ms += max(duration_ms, 0)

    def record_retry(self):
        with self._lock:
            self.retry_count += 1

    def record_transient_failure(self):
        with self._lock:
            self.transient_failures += 1

    def record_permanent_failure(self):
        with self._lock:
            self.permanent_failures += 1

    def record_timeout(self):
        with self._lock:
            self.timeout_count += 1

    def snapshot(self):
        """Copia numérica de las métricas (sin referencias al estado interno)."""
        with self._lock:
            return {
                "total_calls": self.total_calls,
                "provider_calls": self.provider_calls,
                "successful_calls": self.successful_calls,
                "failed_calls": self.failed_calls,
                "retry_count": self.retry_count,
                "transient_failures": self.transient_failures,
                "permanent_failures": self.permanent_failures,
                "timeout_count": self.timeout_count,
                "total_duration_ms": self.total_duration_ms,
            }


# Instancia única del proceso (se pierde al reiniciar, por diseño).
metrics = AIMetrics()