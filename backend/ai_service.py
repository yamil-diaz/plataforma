"""Orquestador de la IA de Aeternum (FASE 8.4).

Pieza central responsable de coordinar TODA solicitud de IA. server.py solo
autentica, valida Pydantic y delega aquí; ningún otro módulo conoce el detalle
de proveedores, contexto o economía.

Flujo de una solicitud:
  1. AUTH                     identidad SIEMPRE desde JWT (server).
  2. VALIDACIÓN               mensaje presente, tamaño, tipos.
  3. PERSISTENCIA (8.7)       resolver conversación (crear si no llega
                              conversation_id; 404 si no es del JWT), cargar
                              su historial y guardar el mensaje del usuario.
  4. ESTADO ECONÓMICO         pre-chequeo de saldo SIN reserva (economía
                              inactiva por defecto; costos PENDIENTES).
  5. LÍMITES TÉCNICOS         ventana de conversación (20 msgs / 8000 chars).
  6. CONSTRUCCIÓN DE CONTEXTO jerarquía: oficial > libro > conversación > general.
  7. CONSTRUCCIÓN DE MENSAJES system + user (libro SIEMPRE como DATOS).
  8. PROVEEDOR                selección (config estricta) + llamada + duración.
                              FASE 8.8: máximo 1 retry técnico para fallos
                              transitorios (timeout / no disponible / respuesta
                              fallida reintentable). Nunca se reintenta un error
                              no transitorio ni se duplica cobro o mensaje.
  9. VALIDACIÓN DE RESPUESTA  contrato ProviderResult; vacía/inválida -> error.
 10. OPERACIÓN ECONÓMICA      cobro SOLO tras respuesta válida (idempotente
                              por operation_id; FASE 8.5, inactiva por defecto).
 11. PERSISTENCIA (8.7)       guardar el mensaje assistant SOLO si la
                              respuesta fue válida (nunca un assistant falso).
 12. RESPUESTA NORMALIZADA    solo datos seguros (nunca secretos internos).

PERSISTENCIA (FASE 8.7):
  - La conversación y los mensajes persisten SOLO cuando hay conexión (db).
    En su ausencia (pruebas unitarias) el comportamiento es el pre-8.7: no se
    persiste nada y conversation_id se ignora.
  - El historial enviado al modelo es ÚNICAMENTE el de la conversación actual
    (aislamiento estricto por conversación y por usuario).
  - Si el proveedor falla, hace timeout o devuelve respuesta inválida, el
    ENDPOINT revierte la transacción: no queda ningún mensaje huérfano ni
    respuesta falsa (y la economía ya garantiza que no se cobra).
  - La conversación persistida NO es memoria permanente: ai_memory sigue
    desactivada (MEMORY_ENABLED = False).

NO implementado en esta fase (ver ai_rayos.py y fases posteriores):
  - precios, límites económicos, suscripciones y rangos (PENDIENTES)
  - proveedor real, modelos reales, API keys, fallback
  - memoria persistente (ai_memory desactivada)

RETRY TÉCNICO (FASE 8.8) y BACKOFF (FASE 8.9):
  - Máximo 1 reintento (2 intentos en total) SOLO para fallos transitorios:
    AIProviderTimeout, AIProviderUnavailable y respuestas fallidas con
    retryable=True en ProviderResult.
  - El ÚNICO reintento va precedido de una espera configurable por el
    servidor (AI_RETRY_DELAY_MS; default técnico 100 ms; 0 = sin espera;
    inválido/negativo -> default seguro; tope 5000 ms). Nunca es
    configurable desde el cliente y nunca aumenta el número de intentos.
    No hay backoff exponencial: es exactamente UN delay antes del retry.
  - Nunca se reintenta un AIProviderError no transitorio (retryable=False)
    ni una excepción inesperada.
  - El reintento NO duplica cobros: charge_operation ocurre una sola vez,
    tras la respuesta VÁLIDA, con el mismo operation_id (idempotente).
  - El reintento NO duplica mensajes persistidos: el mensaje del usuario se
    guarda una vez (paso 3) y el assistant una vez (paso 11, tras respuesta
    válida). Si ambos intentos fallan, el endpoint revierte la transacción
    (no queda ningún mensaje huérfano ni cobro).

OBSERVABILIDAD (FASE 8.9):
  - ai_observability.metrics mantiene contadores EN MEMORIA (por proceso):
    total_calls, provider_calls, successful_calls, failed_calls,
    retry_count, transient_failures, permanent_failures, timeout_count,
    total_duration_ms. Una operación con retry es UNA operación lógica en
    total_calls; los intentos reales se cuentan en provider_calls.
  - Las métricas solo contienen números (nunca prompts, respuestas,
    contenido de libros, JWT, cookies, API keys ni secretos) y se pierden
    al reiniciar el proceso (sin persistencia en BD).

ECONOMÍA (FASE 8.5):
  - PUNTO DE COBRO: SOLO después de una respuesta VÁLIDA. Si el proveedor
    falla, hace timeout o devuelve respuesta inválida -> NO se cobra (no es
    un reembolso: no existe débito).
  - PRE-CHEQUEO DE SALDO sin reserva: evita gastar llamadas si el usuario no
    puede pagar; no bloquea saldo (el débito real es atómico y posterior).
  - IDEMPOTENCIA: operation_id UNIQUE en ai_consumption; un mismo id nunca
    produce doble cobro (retries, doble submit o concurrencia).
  - SALDO NUNCA NEGATIVO: _debit_rayos_atomic (UPDATE condicional).
  - historical_rayos NO se toca.
  - Con costos PENDIENTES (None), aunque la economía esté activada por
    configuración, NUNCA se cobra (no_charge): no se crea dinero artificial.

IDEMPOTENCIA (contrato preparado, sin cobros):
  operation_id opcional: cuando exista economía, cada operación económica se
  asociará a UN operation_id para evitar doble-cobro por reintentos HTTP.
  Hoy se acepta y se propaga en options sin generar ninguna acción.

CONVERSACIÓN (FASE 8.7):
  conversation_id opcional: si llega, se valida que la conversación exista y
  pertenezca al usuario del JWT (404 genérico si no); si no llega, se crea una
  nueva conversación del usuario. NUNCA se confía en él para identidad ni
  acceso (el user_id siempre proviene del JWT). La persistencia requiere
  conexión (db); en su ausencia el contrato queda inerte.
"""

import logging
import os
import time

from ai_context import (
    AIContextError,
    build_system_prompt,
    build_official_context,
    build_book_context,
)
from ai_memory import build_conversation_window
from ai_providers import (
    AIProviderError,
    AIProviderTimeout,
    AIProviderConfigError,
    ProviderResult,
    get_provider,
)
import ai_rayos
import ai_conversations
from ai_observability import metrics

logger = logging.getLogger("aeternum.ai")

MAX_MESSAGE_CHARS = 4000

# ── Backoff del retry técnico (FASE 8.9) ─────────────────────────────────────
# AI_RETRY_DELAY_MS es configuración del SERVIDOR (nunca del cliente): espera
# en milisegundos antes del ÚNICO reintento técnico. Ausente -> 100 ms (valor
# por defecto técnico); "0" -> sin espera; inválido o negativo -> 100 ms
# (default seguro); valores excesivos -> tope técnico de 5000 ms (nunca
# bloquea indefinidamente). No existe backoff exponencial.
AI_RETRY_DELAY_DEFAULT_MS = 100
AI_RETRY_DELAY_MAX_MS = 5000


def _get_retry_delay_ms():
    """Espera configurable antes del único reintento (FASE 8.9)."""
    raw = os.getenv("AI_RETRY_DELAY_MS")
    if raw is None:
        return AI_RETRY_DELAY_DEFAULT_MS
    try:
        value = int(str(raw).strip())
    except (TypeError, ValueError):
        return AI_RETRY_DELAY_DEFAULT_MS
    if value < 0:
        return AI_RETRY_DELAY_DEFAULT_MS
    return min(value, AI_RETRY_DELAY_MAX_MS)


async def _sleep_seconds(seconds):
    """Espera no bloqueante (inyectable en tests)."""
    import asyncio

    await asyncio.sleep(seconds)


class AIServiceError(Exception):
    """Error del servicio de IA. El detail es seguro para el usuario."""

    def __init__(self, detail, status_code=400):
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


def _build_messages(user, message, book_id, page_number, chapter_id,
                    can_access_book, db, history):
    """Pasos 4-6: límites técnicos + contexto + mensajes finales."""
    context_parts = [build_official_context()]

    if book_id is not None:
        context_parts.append(
            build_book_context(
                user,
                book_id,
                page_number=page_number,
                chapter_id=chapter_id,
                can_access_book=can_access_book,
                db=db,
            )
        )

    conversation_window = build_conversation_window(history or [])
    if conversation_window:
        context_parts.append(conversation_window)

    user_content = (
        "\n".join(context_parts)
        + f"\nPregunta del usuario: {message}"
    )

    return [
        {"role": "system", "content": build_system_prompt()},
        {"role": "user", "content": user_content},
    ]


def _normalize_provider_result(raw, active_provider):
    """Paso 8: valida y normaliza la respuesta del proveedor.

    Acepta ProviderResult (contrato oficial) o un dict retrocompatible con
    las claves content/usage. Cualquier otro formato es inválido.
    """
    if isinstance(raw, ProviderResult):
        return raw
    if isinstance(raw, dict):
        text = raw.get("content")
        if not isinstance(text, str):
            raise AIServiceError(
                "El servicio de IA devolvió una respuesta inválida", 500
            )
        return ProviderResult(
            success=True,
            text=text,
            provider=raw.get("provider") or active_provider.name,
            model=raw.get("model") or active_provider.model,
            usage=raw.get("usage") if isinstance(raw.get("usage"), dict) else None,
            retryable=bool(raw.get("retryable", False)),
        )
    raise AIServiceError("El servicio de IA devolvió una respuesta inválida", 500)


async def process_chat(user, message, book_id=None, page_number=None,
                       chapter_id=None, provider=None, can_access_book=None,
                       db=None, history=None, operation_id=None,
                       conversation_id=None):
    """Procesa una petición de chat y devuelve la respuesta normalizada.

    - user: dict del usuario autenticado (SIEMPRE desde JWT; cualquier
      user_id recibido del frontend se ignora).
    - provider: si es None, se usa el proveedor configurado (mock en esta
      fase). Los tests inyectan proveedores simulados.
    - can_access_book: política de acceso a libros (server._puede_acceder_libro).
    - db: conexión de base de datos abierta por el endpoint. Si es None no
      hay persistencia (modo de prueba unitaria; comportamiento pre-8.7).
    - history: historial de respaldo usado SOLO cuando no hay persistencia.
      Con persistencia activa, el historial es SIEMPRE el de la conversación
      actual (nunca se mezclan conversaciones).
    - operation_id: clave de idempotencia económica (sin efecto económico hoy).
    - conversation_id: conversación del usuario (se valida contra el JWT;
      si no llega, se crea una nueva). Solo aplica con persistencia activa.
    """
    start = time.perf_counter()

    # 1. AUTH: la identidad proviene SIEMPRE del JWT (server.py).
    if not user or not user.get("id"):
        raise AIServiceError("Usuario no autenticado", 401)

    # 2. VALIDACIÓN de la solicitud.
    if not message or not str(message).strip():
        raise AIServiceError("El mensaje no puede estar vacío", 400)
    message = str(message).strip()
    if len(message) > MAX_MESSAGE_CHARS:
        raise AIServiceError(
            f"El mensaje supera el límite de {MAX_MESSAGE_CHARS} caracteres", 400
        )

    # 3. PERSISTENCIA DE CONVERSACIÓN (FASE 8.7): resolver la conversación del
    #    JWT, cargar su historial y guardar el mensaje del usuario. Con db
    #    presente (endpoint) la validación de ownership es OBLIGATORIA: una
    #    conversación ajena produce el mismo 404 que una inexistente.
    #    Sin db (pruebas unitarias) no hay persistencia y el contrato queda
    #    inerte (conversation_id se ignora, como en FASES 8.3-8.6).
    persisted_history = None
    if db is not None:
        try:
            if conversation_id is None:
                conversation = ai_conversations.create_conversation(db, user["id"])
            else:
                conversation = ai_conversations.resolve_conversation(
                    db, conversation_id, user["id"]
                )
            conversation_id = conversation["id"]
            rows = ai_conversations.get_messages(db, conversation_id, user["id"])
            persisted_history = [
                {"role": m["role"], "content": m["content"]} for m in rows
            ]
            ai_conversations.add_message(db, conversation_id, "user", message)
        except ai_conversations.AIConversationError as e:
            raise AIServiceError(e.detail, e.status_code)
        except Exception:
            logger.exception(
                "Error inesperado al persistir la conversación (usuario_id=%s)",
                user["id"],
            )
            raise AIServiceError("No se pudo guardar la conversación", 500)
    else:
        # Sin conexión (modo de prueba unitaria) no hay persistencia: el
        # contrato conversation_id queda inerte, como en FASES 8.3-8.6.
        conversation_id = None

    # 4. ESTADO ECONÓMICO: consulta explícita del estado de la economía.
    #    INACTIVA por defecto (configuración explícita AI_ECONOMY_ENABLED).
    #    Con costos PENDIENTES nunca se cobra, aunque esté activada.
    economy_active = ai_rayos.is_economy_active()
    if economy_active:
        operation_cost = ai_rayos.estimate_operation_cost(
            "chat", context={"operation_id": operation_id}
        )
        # PRE-CHEQUEO DE SALDO SIN RESERVA: si el usuario no puede pagar, no
        # se gasta una llamada al proveedor. No bloquea ni descuenta nada.
        if db is not None and not ai_rayos.precheck_balance(db, user["id"], operation_cost):
            raise AIServiceError("No tienes suficientes Rayos para esta operación", 400)
    else:
        operation_cost = None

    # 5-7. Límites técnicos, construcción de contexto y mensajes.
    try:
        messages = _build_messages(
            user, message, book_id, page_number, chapter_id,
            can_access_book, db,
            persisted_history if persisted_history is not None else history,
        )
    except AIContextError as e:
        raise AIServiceError(e.detail, e.status_code)

    # 8. PROVEEDOR: selección estricta + llamada con medición de duración.
    active_provider = provider
    if active_provider is None:
        try:
            active_provider = get_provider()
        except AIProviderConfigError:
            # Configuración inválida: NUNCA cae silenciosamente a Mock.
            # Se devuelve un 500 genérico y seguro (sin detalles internos).
            logger.error(
                "Configuración de IA inválida (usuario_id=%s)", user["id"],
                exc_info=True,
            )
            raise AIServiceError(
                "El servicio de IA no está configurado correctamente", 500
            )

    options = {
        "user_id": user["id"],
        "operation": "chat",
        "operation_id": operation_id,
    }

    # 8. PROVEEDOR con RETRY TÉCNICO (FASE 8.8) y BACKOFF (FASE 8.9): máximo
    #    1 reintento (2 intentos en total), SOLO para fallos transitorios, y
    #    precedido por una espera configurable del servidor
    #    (AI_RETRY_DELAY_MS; 0 = sin espera; nunca configurable por el
    #    cliente). Nunca se reintenta un error no transitorio ni una excepción
    #    inesperada. El reintento no duplica cobros (cobro único tras respuesta
    #    válida) ni mensajes persistidos (user una vez en paso 3, assistant una
    #    vez en paso 11). Cada operación lógica se registra en las métricas de
    #    observabilidad (total_calls; el retry suma en provider_calls).
    RETRY_MAX = 1
    raw = None
    result = None
    metrics.record_call_start()
    try:
        for attempt in range(RETRY_MAX + 1):
            metrics.record_provider_call()
            try:
                raw = await active_provider.chat(messages, options)
            except AIProviderTimeout:
                metrics.record_timeout()
                if attempt < RETRY_MAX:
                    metrics.record_transient_failure()
                    metrics.record_retry()
                    logger.warning(
                        "Timeout de IA, reintento técnico %s/2 "
                        "(usuario_id=%s provider=%s)",
                        attempt + 1, user["id"], active_provider.name,
                    )
                    await _sleep_seconds(_get_retry_delay_ms() / 1000.0)
                    continue
                metrics.record_transient_failure()
                raise AIServiceError(
                    "El servicio de IA tardó demasiado en responder. "
                    "Inténtalo de nuevo.",
                    503,
                )
            except AIProviderError as exc:
                if exc.retryable and attempt < RETRY_MAX:
                    metrics.record_transient_failure()
                    metrics.record_retry()
                    logger.warning(
                        "Proveedor de IA no disponible, reintento técnico %s/2 "
                        "(usuario_id=%s provider=%s)",
                        attempt + 1, user["id"], active_provider.name,
                    )
                    await _sleep_seconds(_get_retry_delay_ms() / 1000.0)
                    continue
                if exc.retryable:
                    # Segundo intento transitorio: fallo final transitorio.
                    metrics.record_transient_failure()
                else:
                    metrics.record_permanent_failure()
                raise AIServiceError(
                    "El servicio de IA no está disponible en este momento. "
                    "Inténtalo más tarde.",
                    503,
                )
            except Exception:
                # Excepción inesperada del proveedor -> error seguro (500 genérico).
                # Nunca se reintenta: no es un fallo transitorio conocido.
                metrics.record_permanent_failure()
                logger.exception(
                    "Error inesperado del proveedor de IA (usuario_id=%s provider=%s)",
                    user["id"], active_provider.name,
                )
                raise AIServiceError("Error interno del servicio de IA", 500)

            # 8. VALIDACIÓN DE RESPUESTA: contrato ProviderResult. Una respuesta
            #    fallida pero marcada como reintentable también se reintenta UNA
            #    vez (FASE 8.8); el fallo definitivo produce error seguro.
            result = _normalize_provider_result(raw, active_provider)
            if not result.success or not result.text or not result.text.strip():
                if result.retryable and attempt < RETRY_MAX:
                    metrics.record_transient_failure()
                    metrics.record_retry()
                    logger.warning(
                        "Respuesta de IA fallida reintentable, reintento técnico "
                        "%s/2 (usuario_id=%s provider=%s)",
                        attempt + 1, user["id"], active_provider.name,
                    )
                    await _sleep_seconds(_get_retry_delay_ms() / 1000.0)
                    continue
                if result.retryable:
                    metrics.record_transient_failure()
                else:
                    metrics.record_permanent_failure()
                logger.warning(
                    "Respuesta de IA vacía o fallida (usuario_id=%s provider=%s)",
                    user["id"], active_provider.name,
                )
                raise AIServiceError("El servicio de IA devolvió una respuesta inválida", 500)
            break
    except AIServiceError:
        # Operación lógica terminada sin éxito: se registra failed_calls y la
        # duración total (backoff incluido). Los fallos previos al proveedor
        # (validación, persistencia, saldo) no son llamadas de IA: no se
        # registran aquí.
        metrics.record_failure(int((time.perf_counter() - start) * 1000))
        raise

    duration_ms = int((time.perf_counter() - start) * 1000)

    # Operación lógica terminada con éxito (una sola vez, aunque hubo retry).
    metrics.record_success(duration_ms)

    if result.duration_ms is None:
        result.duration_ms = duration_ms

    # 10. OPERACIÓN ECONÓMICA (punto de cobro: SOLO tras respuesta válida).
    #    Si el proveedor falló/timeout/respuesta inválida, aquí NO se llega
    #    (no hay cobro). charge_operation gestiona su propia transacción.
    try:
        econ_result = ai_rayos.charge_operation(
            db=db,
            user_id=user["id"],
            operation_id=operation_id,
            operation="chat",
            cost=operation_cost,
            provider=result.provider or active_provider.name,
            model=result.model or active_provider.model,
            duration_ms=result.duration_ms,
        )
    except Exception:
        logger.exception(
            "Error inesperado en la operación económica de IA "
            "(usuario_id=%s)", user["id"],
        )
        raise AIServiceError("No se pudo completar la operación", 500)

    econ_status = econ_result.get("status")
    if econ_status == "insufficient_balance":
        raise AIServiceError("No tienes suficientes Rayos para esta operación", 400)
    if econ_status == "rejected":
        # El operation_id pertenece a otro usuario: nunca se expone ni se
        # permite gastar Rayos de nadie más.
        logger.warning(
            "operation_id de otro usuario (usuario_id=%s)", user["id"],
        )
        raise AIServiceError("Operación no válida", 400)
    # charged | no_charge | inactive | already_processed -> la respuesta se
    # entrega igual: ya_processed no es un error (sin doble cobro).

    # 11. PERSISTENCIA DE LA RESPUESTA (FASE 8.7): SOLO si el proveedor
    #     devolvió una respuesta VÁLIDA (paso 9 ya lo garantizó). Nunca se
    #     guarda una respuesta fallida/vacía. El mensaje del usuario quedó
    #     guardado en el paso 3.
    if db is not None:
        try:
            ai_conversations.add_message(db, conversation_id, "assistant", result.text)
        except Exception:
            logger.exception(
                "No se pudo guardar la respuesta de IA (usuario_id=%s)",
                user["id"],
            )
            raise AIServiceError("No se pudo guardar la respuesta", 500)

    logger.info(
        "Operación IA completada (usuario_id=%s provider=%s model=%s "
        "duracion_ms=%s economia=%s)",
        user["id"], result.provider or active_provider.name,
        result.model or active_provider.model, result.duration_ms,
        econ_status,
    )

    # 12. RESPUESTA NORMALIZADA: solo datos seguros, sin secretos ni
    #     detalles internos. conversation_id es el de la conversación
    #     persistida (o None sin persistencia).
    return {
        "success": True,
        "message": result.text,
        "provider": result.provider or active_provider.name,
        "model": result.model or active_provider.model,
        "conversation_id": conversation_id,
        "usage": result.usage,
    }