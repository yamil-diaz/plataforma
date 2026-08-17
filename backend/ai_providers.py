"""Proveedores de IA de Aeternum (FASE 8.4 — contrato normalizado;
FASE 8.14 — adaptador real Gemini).

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

En esta fase existen DOS adaptadores del mismo contrato:
  - MockAIProvider: simulación (sin Internet, sin API key), explícito para
    desarrollo y tests.
  - GeminiAIProvider (FASE 8.14): proveedor real Google Gemini mediante el
    SDK oficial google-genai. NO activa la economía de Rayos (costos
    PENDIENTES: AI_COST_CHAT=None, AI_ECONOMY_ENABLED desactivada).

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

CONFIGURACIÓN (FASE 8.14):
  AI_PROVIDER  -> nombre del adaptador registrado ("mock" | "gemini").
  AI_MODEL     -> nombre del modelo; solo aplica a proveedores reales.
                 Default Gemini: "gemini-3.6-flash".
  GEMINI_API_KEY -> ÚNICA fuente de la clave de Gemini (variable de entorno;
                 nunca en código, logs, frontend ni respuestas). Si
                 AI_PROVIDER="gemini" y la clave no existe, el adaptador
                 falla de forma controlada con AIProviderConfigError (NUNCA
                 cae silenciosamente a Mock).

REGLA DE CONFIGURACIÓN (FASE 8.4):
  - AI_PROVIDER ausente  -> mock SOLO si no estamos en producción (default
                            seguro de desarrollo/test, provisional).
  - AI_PROVIDER="mock"   -> mock explícito (siempre válido).
  - AI_PROVIDER con nombre no registrado -> AIProviderConfigError.
    NUNCA se convierte silenciosamente un nombre desconocido en Mock.
"""

import os
from dataclasses import dataclass, field

# ── Configuración técnica del adaptador Gemini (FASE 8.14) ──────────────────
GEMINI_DEFAULT_MODEL = "gemini-3.6-flash"
GEMINI_TIMEOUT_DEFAULT_MS = 60000
GEMINI_MAX_OUTPUT_TOKENS_DEFAULT = 2048
GEMINI_TEMPERATURE_DEFAULT = 0.7


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


def _read_int_env(name, default):
    """Lee una variable numérica de entorno con fallback seguro."""
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = int(str(raw).strip())
    except (TypeError, ValueError):
        return default
    return value if value > 0 else default


class GeminiAIProvider(AIProvider):
    """Proveedor real Google Gemini (FASE 8.14) con el SDK oficial
    google-genai.

    Traduce el contrato interno (messages: lista de dicts role/content) al
    formato de Gemini: el/los mensajes "system" se convierten en
    system_instruction y los roles assistant -> "model", user -> "user".
    NO construye contexto: recibe SIEMPRE el contenido ya construido por
    ai_service (system prompt + historial + mensaje actual).

    La API key se lee EXCLUSIVAMENTE de la variable de entorno
    GEMINI_API_KEY (nunca hardcodeada, logueada, enviada al frontend ni
    incluida en respuestas). Si falta y no se inyecta un cliente, la
    construcción falla con AIProviderConfigError (configuración ausente:
    NUNCA Mock silencioso).

    CICLO DE VIDA DEL CLIENTE (FASE 8.14.2):
      - Un cliente inyectado (tests/inyección externa) se usa tal cual y
        NUNCA se cierra (quien lo inyectó lo gestiona).
      - Cuando el adaptador crea el cliente (sin inyección), crea uno POR
        LLAMADA chat() y lo cierra en finally (await client.aio.aclose()
        + client.close(), mecanismo oficial de google-genai==2.18.1,
        idempotente en httpx 0.28). Nunca hay un cliente global que
        mezcle configuraciones entre usuarios, y el retry técnico de
        ai_service funciona porque cada intento usa un cliente propio.

    Manejo de errores (mapeado al contrato de ai_service):
      - timeout de red (httpx.TimeoutException)      -> AIProviderTimeout
      - conectividad/errores 5xx/429                 -> AIProviderUnavailable
      - errores permanentes 4xx (menos 429)          -> AIProviderError no
                                                       retryable
      - respuesta vacía (sin texto)                  -> ProviderResult
                                                       fallido (error seguro)
    """

    name = "gemini"

    def __init__(self, config=None, client=None):
        super().__init__(config)
        self.model = (
            (config or {}).get("model")
            or (os.getenv("AI_MODEL") or "").strip()
            or GEMINI_DEFAULT_MODEL
        )
        self.timeout_ms = _read_int_env(
            "AI_GEMINI_TIMEOUT_MS", GEMINI_TIMEOUT_DEFAULT_MS
        )
        self.max_output_tokens = _read_int_env(
            "AI_GEMINI_MAX_OUTPUT_TOKENS", GEMINI_MAX_OUTPUT_TOKENS_DEFAULT
        )
        self.temperature = GEMINI_TEMPERATURE_DEFAULT
        raw_temp = os.getenv("AI_GEMINI_TEMPERATURE")
        if raw_temp is not None:
            try:
                parsed = float(str(raw_temp).strip())
                if 0.0 <= parsed <= 2.0:
                    self.temperature = parsed
            except (TypeError, ValueError):
                pass
        self._client = client
        self._owns_client = client is None
        if self._owns_client:
            # Validación TEMPRANA de configuración: sin GEMINI_API_KEY el
            # adaptador falla al construirse (error controlado en la selección
            # del proveedor, nunca Mock silencioso). El cliente real NO se
            # crea aquí: se crea por llamada y se cierra en chat() (ciclo de
            # vida controlado, FASE 8.14.2).
            self._read_api_key()

    def _read_api_key(self):
        """Clave SOLO desde la variable GEMINI_API_KEY.

        Nunca se hardcodea, loguea, envía al frontend ni se incluye en
        respuestas. Ausente -> AIProviderConfigError (configuración ausente).
        """
        api_key = (os.getenv("GEMINI_API_KEY") or "").strip()
        if not api_key:
            raise AIProviderConfigError(
                "Clave de API de Gemini ausente (GEMINI_API_KEY)",
                provider=self.name,
                model=self.model,
            )
        return api_key

    def _build_client(self):
        """Construye un cliente oficial google-genai (por llamada).

        Cada llamada de chat() crea su propio cliente (nunca un global que
        mezcle configuraciones) y lo cierra al terminar. La clave se lee
        SOLO de GEMINI_API_KEY.
        """
        api_key = self._read_api_key()
        from google import genai
        from google.genai import types

        return genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(timeout=self.timeout_ms),
        )

    @staticmethod
    async def _close_client(client):
        """Cierra el cliente SOLO cuando el adaptador lo creó (nunca
        clientes inyectados por tests). Best-effort: un fallo de cierre
        jamás enmascara la respuesta ni el error de la llamada.

        Mecanismo soportado por google-genai==2.18.1:
          - Client.aio.aclose() -> cierra el cliente ASYNC (el único que usa
            este adaptador) y es idempotente (httpx 0.28 guarda por estado
            CLOSED; el transporte se crea en el constructor, nunca None).
          - Client.close()      -> cierra el cliente sync (también creado
            por el constructor del SDK; se cierra por completitud).
        """
        try:
            await client.aio.aclose()
        except Exception:
            pass
        try:
            client.close()
        except Exception:
            pass

    @staticmethod
    def _extract_system_instruction(messages):
        """Junta los mensajes system (construidos por ai_service) en la
        system_instruction de Gemini."""
        parts = [
            str(m.get("content")).strip()
            for m in messages or []
            if m.get("role") == "system" and str(m.get("content") or "").strip()
        ]
        return "\n\n".join(parts) or None

    @staticmethod
    def _to_gemini_contents(messages):
        """Convierte los mensajes ya construidos por ai_service al formato
        de Gemini: assistant -> role "model", user -> role "user". Los
        mensajes system NO van en contents (van en system_instruction).
        Mensajes consecutivos del mismo rol se fusionan (Gemini no permite
        dos turnos seguidos del mismo rol en algunos modelos)."""
        from google.genai import types

        contents = []
        for msg in messages or []:
            role = msg.get("role")
            content = str(msg.get("content") or "").strip()
            if role == "system" or not content:
                continue
            gemini_role = "model" if role == "assistant" else "user"
            if contents and contents[-1].role == gemini_role:
                contents[-1].parts.append(types.Part(text=content))
            else:
                contents.append(
                    types.Content(role=gemini_role, parts=[types.Part(text=content)])
                )
        return contents

    @staticmethod
    def _map_usage(usage_metadata):
        """Traduce usage_metadata de Gemini al dict de uso del contrato."""
        if usage_metadata is None:
            return None
        return {
            "prompt_tokens": getattr(usage_metadata, "prompt_token_count", None),
            "completion_tokens": getattr(usage_metadata, "candidates_token_count", None),
            "total_tokens": getattr(usage_metadata, "total_token_count", None),
        }

    async def chat(self, messages, options=None):
        """Llamada al modelo Gemini y traducción a ProviderResult.

        Ciclo de vida del cliente (FASE 8.14.2):
          - cliente inyectado (tests): se usa tal cual y NUNCA se cierra.
          - cliente creado por el adaptador: se crea uno POR LLAMADA y se
            cierra en finally (aclose async + close sync, best-effort). El
            retry técnico de ai_service reutiliza el adaptador pero cada
            intento usa un cliente propio y limpio.

        Nunca se registra la API key ni se incluye en options, mensajes,
        resultados o excepciones (errores con texto genérico seguro).
        """
        system_instruction = self._extract_system_instruction(messages)
        contents = self._to_gemini_contents(messages)

        from google.genai import types

        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            max_output_tokens=self.max_output_tokens,
            temperature=self.temperature,
        )
        owns_client = self._owns_client
        client = self._client if not owns_client else self._build_client()
        try:
            response = await client.aio.models.generate_content(
                model=self.model,
                contents=contents,
                config=config,
            )
        except Exception as exc:
            self._raise_mapped(exc)
            raise  # pragma: no cover - _raise_mapped siempre lanza
        finally:
            if owns_client:
                await self._close_client(client)

        text = getattr(response, "text", None)
        if not text or not str(text).strip():
            # Respuesta vacía (sin texto): error seguro, nunca se inventa
            # contenido. No reintentable: no es un fallo transitorio.
            return ProviderResult(
                success=False,
                text="",
                provider=self.name,
                model=self.model,
                usage=self._map_usage(getattr(response, "usage_metadata", None)),
                error_code="empty_response",
                retryable=False,
            )
        return ProviderResult(
            success=True,
            text=str(text).strip(),
            provider=self.name,
            model=self.model,
            usage=self._map_usage(getattr(response, "usage_metadata", None)),
            error_code=None,
            retryable=False,
        )

    def _raise_mapped(self, exc):
        """Mapea errores del SDK de Gemini al contrato de ai_service.

        - httpx.TimeoutException            -> AIProviderTimeout (retryable).
        - errores de red (httpx.ConnectError, NetworkError) y 5xx / 429
          (ServerError, rate limit)         -> AIProviderUnavailable.
        - errores permanentes del cliente (4xx, p.ej. 400/401/403/404)
          (ClientError)                     -> AIProviderError NO retryable.
        Los mensajes de excepción NUNCA incluyen la clave ni detalle del
        proveedor: solo texto genérico seguro.
        """
        try:
            import httpx
        except ImportError:  # pragma: no cover - httpx es dependencia del SDK
            httpx = None
        if httpx is not None and isinstance(exc, httpx.TimeoutException):
            raise AIProviderTimeout(
                "Timeout del proveedor Gemini",
                provider=self.name,
                model=self.model,
            )
        if httpx is not None and isinstance(
            exc, (httpx.ConnectError, httpx.NetworkError)
        ):
            raise AIProviderUnavailable(
                "Proveedor Gemini no disponible (error de red)",
                provider=self.name,
                model=self.model,
            )
        from google.genai import errors

        if isinstance(exc, errors.ServerError):
            raise AIProviderUnavailable(
                "Proveedor Gemini no disponible (error del servicio)",
                provider=self.name,
                model=self.model,
            )
        if isinstance(exc, errors.ClientError):
            if getattr(exc, "code", None) == 429:
                raise AIProviderUnavailable(
                    "Proveedor Gemini limitado temporalmente",
                    provider=self.name,
                    model=self.model,
                )
            raise AIProviderError(
                "Error permanente del proveedor Gemini",
                provider=self.name,
                model=self.model,
                retryable=False,
            )
        if isinstance(exc, errors.APIError):
            raise AIProviderUnavailable(
                "Proveedor Gemini no disponible (respuesta inesperada)",
                provider=self.name,
                model=self.model,
            )
        raise


# ── Registro de proveedores ────────────────────────────────────────────────
_PROVIDER_REGISTRY = {
    "mock": lambda config: MockAIProvider(config=config),
    "gemini": lambda config: GeminiAIProvider(config=config),
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
    - AI_PROVIDER registrado: se construye el adaptador correspondiente
      ("mock" siempre válido; "gemini" exige GEMINI_API_KEY, en su ausencia
      AIProviderConfigError).
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