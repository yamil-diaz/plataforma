"""Proveedores de IA de Aeternum (FASE 8.4 — contrato normalizado).

Capa de abstracción AIProvider: el orquestador (ai_service) habla con esta
interfaz y NUNCA conoce detalles de un proveedor concreto (OpenAI, Gemini,
Anthropic, Groq, ...).

CONTRATO DE RESPUESTA (ProviderResult):
  Todo proveedor devuelve un ProviderResult normalizado:
    - success:      bool, operación completada correctamente.
    - text:         texto de la respuesta (vacío solo si success=False).
    - provider:     nombre del proveedor.
    - model:        modelo usado.
    - usage:        dict de uso (tokens) o None (siempre None con mock).
    - duration_ms:  duración medida por el orquestador (None si no aplica).
    - error_code:   código de error interno del proveedor (solo si falla).
    - retryable:    si el error es reintentable (FASE 8.8: 1 retry técnico
                    máximo; ai_service reintenta UNA vez los fallos
                    transitorios marcados como reintentables).

En esta fase SOLO existe MockAIProvider (sin Internet, sin API key), explícito
para desarrollo y tests. Los proveedores reales se añadirán en fases
posteriores como adaptadores de esta misma interfaz.

RETRY TÉCNICO (FASE 8.8):
  - Máximo 1 reintento (2 intentos en total) SOLO para fallos transitorios:
    AIProviderTimeout y AIProviderUnavailable se marcan retryable por defecto.
  - Un AIProviderError genérico (no transitorio, sin marca retryable) NO se
    reintenta jamás.
  - Una respuesta fallida con retryable=True en ProviderResult también se
    reintenta UNA vez.
  - El reintento no duplica cobros (la economía solo descuenta tras una
    respuesta VÁLIDA) ni mensajes persistidos (el assistant se guarda una
    sola vez, tras la respuesta válida).

CONFIGURACIÓN (conceptual, sin claves todavía):
  AI_PROVIDER  -> nombre del adaptador registrado ("mock" es el único hoy).
  AI_MODEL     -> nombre del modelo; solo aplica a proveedores reales
                  (fase posterior). El mock reporta model="mock".
  No se exige ni se lee AI_API_KEY_* en esta fase.

REGLA DE CONFIGURACIÓN (FASE 8.4):
  - AI_PROVIDER ausente  -> mock SOLO si no estamos en producción (default
                            seguro de desarrollo/test, provisional).
  - AI_PROVIDER="mock"   -> mock explícito (siempre válido).
  - AI_PROVIDER con nombre no registrado -> AIProviderConfigError.
    NUNCA se convierte silenciosamente un nombre desconocido en Mock.
"""

import os
from dataclasses import dataclass, field


class AIProviderError(Exception):
    """Error genérico del proveedor. El detalle interno NUNCA se expone al
    usuario final; ai_service lo traduce a un mensaje seguro."""

    def __init__(self, message, provider=None, model=None, retryable=False):
        super().__init__(message)
        self.provider = provider
        self.model = model
        self.retryable = retryable


class AIProviderTimeout(AIProviderError):
    """El proveedor excedió el tiempo máximo de respuesta.

    Transitorio por naturaleza: ai_service lo reintenta UNA vez (FASE 8.8).
    """

    def __init__(self, message, provider=None, model=None, retryable=True):
        super().__init__(message, provider, model, retryable)


class AIProviderUnavailable(AIProviderError):
    """El proveedor no está disponible (red, credenciales, mantenimiento).

    Transitorio por naturaleza: ai_service lo reintenta UNA vez (FASE 8.8).
    """

    def __init__(self, message, provider=None, model=None, retryable=True):
        super().__init__(message, provider, model, retryable)


class AIProviderConfigError(AIProviderError):
    """Configuración de IA inválida (proveedor desconocido o no registrado).

    NO se convierte en Mock: una mala configuración debe fallar de forma
    explícita y controlada, nunca ocultarse.
    """


@dataclass
class ProviderResult:
    """Resultado normalizado de una llamada a un proveedor de IA.

    Es el ÚNICO formato que el orquestador entiende. Un proveedor real debe
    traducir su formato propietario a ProviderResult dentro de su adaptador.
    """

    success: bool
    text: str
    provider: str = ""
    model: str = ""
    usage: dict = None
    duration_ms: int = None
    error_code: str = None
    retryable: bool = False


class AIProvider:
    """Interfaz base de un proveedor de IA.

    chat(messages, options) -> ProviderResult

    messages: lista de dicts {"role": "system"|"user"|"assistant", "content": str}
    options:  dict de metadata segura (user_id, operation, operation_id, ...).
              NUNCA contiene secretos ni credenciales.
    """

    name = "base"
    model = "base"

    def __init__(self, config=None):
        self.config = config or {}

    async def chat(self, messages, options=None):
        raise NotImplementedError("Cada proveedor debe implementar chat()")


class MockAIProvider(AIProvider):
    """Proveedor de simulación: funciona sin Internet y sin API key.

    Modos de comportamiento (para tests y desarrollo local):
      - success: responde un mensaje fijo determinista.
      - error:   lanza AIProviderUnavailable (proveedor caído).
      - timeout: lanza AIProviderTimeout (excedió el tiempo de respuesta).
    """

    name = "mock"
    model = "mock"

    def __init__(self, mode="success", delay_ms=0, config=None):
        super().__init__(config)
        if mode not in ("success", "error", "timeout"):
            raise ValueError(f"Modo MockAIProvider no válido: {mode}")
        self.mode = mode
        self.delay_ms = delay_ms

    async def chat(self, messages, options=None):
        if self.delay_ms:
            await _sleep(self.delay_ms / 1000.0)
        if self.mode == "error":
            raise AIProviderUnavailable(
                "MockAIProvider en modo error (simulación de proveedor caído)",
                provider=self.name,
                model=self.model,
            )
        if self.mode == "timeout":
            raise AIProviderTimeout(
                "MockAIProvider en modo timeout (simulación de respuesta lenta)",
                provider=self.name,
                model=self.model,
            )
        return ProviderResult(
            success=True,
            text=(
                "Respuesta simulada del asistente de Aeternum (modo de "
                "prueba, sin proveedor externo)."
            ),
            provider=self.name,
            model=self.model,
            usage=None,
            error_code=None,
            retryable=False,
        )


async def _sleep(seconds):
    """Sleep sin bloqueo compatible con el asyncio del servidor."""
    import asyncio

    await asyncio.sleep(seconds)


# ── Registro de proveedores ────────────────────────────────────────────────
_PROVIDER_REGISTRY = {
    "mock": lambda config: MockAIProvider(config=config),
}


def _is_production():
    """Entorno de producción según la variable ENV del proyecto.

    Provisional: si ENV no está definida se considera desarrollo/test, donde
    el mock es el default seguro permitido.
    """
    return (os.getenv("ENV") or "").strip().lower() == "production"


def get_provider(config=None):
    """Devuelve el proveedor activo según configuración segura.

    - AI_PROVIDER ausente: default mock SOLO fuera de producción (provisional
      para desarrollo/tests). En producción exige configuración explícita.
    - AI_PROVIDER registrado: se construye el adaptador correspondiente.
    - AI_PROVIDER desconocido: AIProviderConfigError (NUNCA mock silencioso).
    """
    name = (os.getenv("AI_PROVIDER") or "").strip().lower()
    if not name:
        if _is_production():
            raise AIProviderConfigError(
                "Proveedor de IA no configurado en producción",
                provider=None,
            )
        name = "mock"
    factory = _PROVIDER_REGISTRY.get(name)
    if factory is None:
        raise AIProviderConfigError(
            f"Proveedor de IA no reconocido: {name}",
            provider=name,
        )
    return factory(config)