"""Tests del adaptador real Gemini (FASE 8.14).

Usan clientes simulados inyectados (fake client): NUNCA se hacen llamadas
reales a la API de Gemini ni se usan API keys reales. Verifican el contrato
ProviderResult, el mapeo de errores, la seguridad de la clave y que la
selección AI_PROVIDER respeta el registro de proveedores."""

import asyncio
import os

import pytest

import httpx
from google.genai import errors as genai_errors

import server
from ai_providers import (
    MockAIProvider,
    GeminiAIProvider,
    AIProviderError,
    AIProviderTimeout,
    AIProviderUnavailable,
    AIProviderConfigError,
    ProviderResult,
    get_provider,
)
from ai_service import process_chat, AIServiceError
import ai_rayos

FAKE_KEY = "FAKE-GEMINI-KEY-SOLO-PARA-TESTS"


def _run(coro):
    return asyncio.run(coro)


# ── Clientes simulados (sin red, sin SDK real) ──────────────────────────────
class FakeUsage:
    prompt_token_count = 10
    candidates_token_count = 5
    total_token_count = 15


class FakeGeminiResponse:
    def __init__(self, text="Respuesta de prueba de Gemini"):
        self.text = text
        self.usage_metadata = FakeUsage()


class _FakeModels:
    """models.generate_content simulado: registra la llamada y devuelve la
    respuesta o lanza la excepción configurada."""

    def __init__(self, owner):
        self.owner = owner

    async def generate_content(self, model=None, contents=None, config=None):
        self.owner.calls += 1
        self.owner.captured.append(
            {"model": model, "contents": contents, "config": config}
        )
        if self.owner.exc is not None:
            raise self.owner.exc
        return self.owner.response


class _FakeAio:
    def __init__(self, owner):
        self.models = _FakeModels(owner)
        self._owner = owner

    async def aclose(self):
        self._owner.aclose_calls += 1


class FakeGeminiClient:
    """Cliente con la misma superficie que google.genai.Client (vía .aio),
    con contadores de cierre para verificar el ciclo de vida (FASE 8.14.2)."""

    def __init__(self, response=None, exc=None):
        self.response = response if response is not None else FakeGeminiResponse()
        self.exc = exc
        self.calls = 0
        self.captured = []
        self.aclose_calls = 0
        self.close_calls = 0
        self.aio = _FakeAio(self)

    def close(self):
        self.close_calls += 1


def _provider(client=None, **kwargs):
    """Adaptador Gemini con cliente inyectado (sin clave real)."""
    return GeminiAIProvider(client=client or FakeGeminiClient(), **kwargs)


# ═══════════════ 1/14. GEMINI SIN API KEY → ERROR SEGURO ════════════════════

def test_gemini_sin_api_key_error_de_configuracion(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "gemini")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(AIProviderConfigError):
        get_provider()


def test_gemini_sin_api_key_no_usa_mock(monkeypatch):
    # AI_PROVIDER=gemini sin clave NUNCA cae silenciosamente a Mock.
    monkeypatch.setenv("AI_PROVIDER", "gemini")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(AIProviderConfigError):
        get_provider()


def test_gemini_sin_api_key_error_seguro_en_servicio(monkeypatch, fake_db):
    monkeypatch.setenv("AI_PROVIDER", "gemini")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(AIServiceError) as excinfo:
        _run(process_chat(user=fake_db.state["users"][1], message="Hola"))
    assert excinfo.value.status_code == 500
    assert "GEMINI_API_KEY" not in excinfo.value.detail
    assert "no está configurado" in excinfo.value.detail


def test_gemini_sin_api_key_endpoint_500_seguro(monkeypatch, as_admin):
    monkeypatch.setenv("AI_PROVIDER", "gemini")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    resp = as_admin.post("/api/ai/chat", json={"message": "Hola"})
    assert resp.status_code == 500
    assert "GEMINI_API_KEY" not in str(resp.json())


# ═══════════════════ 2/14. CONTRATO ProviderResult ══════════════════════════

def test_gemini_contrato_provider_result_correcto():
    client = FakeGeminiClient()
    provider = _provider(client=client)
    result = _run(provider.chat([{"role": "user", "content": "Hola"}]))
    assert isinstance(result, ProviderResult)
    assert result.success is True
    assert result.text == "Respuesta de prueba de Gemini"
    assert result.provider == "gemini"
    assert result.model == "gemini-3.6-flash"
    assert result.error_code is None
    assert result.retryable is False
    assert result.usage == {
        "prompt_tokens": 10,
        "completion_tokens": 5,
        "total_tokens": 15,
    }


def test_gemini_modelo_desde_env(monkeypatch):
    monkeypatch.setenv("AI_MODEL", "gemini-otro-modelo")
    client = FakeGeminiClient()
    provider = _provider(client=client)
    assert provider.model == "gemini-otro-modelo"
    _run(provider.chat([{"role": "user", "content": "Hola"}]))
    assert client.captured[0]["model"] == "gemini-otro-modelo"


# ═══════════════════ 3/14. RESPUESTA DE TEXTO CORRECTA ══════════════════════

def test_gemini_respuesta_texto_exacta():
    client = FakeGeminiClient(response=FakeGeminiResponse("  Texto de Gemini  "))
    result = _run(_provider(client=client).chat(
        [{"role": "user", "content": "Hola"}]
    ))
    assert result.success is True
    assert result.text == "Texto de Gemini"


def test_gemini_transformacion_system_a_system_instruction():
    client = FakeGeminiClient()
    _run(_provider(client=client).chat([
        {"role": "system", "content": "Eres el asistente de Aeternum"},
        {"role": "user", "content": "Hola"},
    ]))
    captured = client.captured[0]
    assert captured["config"].system_instruction == "Eres el asistente de Aeternum"
    roles = [c.role for c in captured["contents"]]
    assert roles == ["user"]


def test_gemini_transformacion_roles_y_fusion():
    client = FakeGeminiClient()
    _run(_provider(client=client).chat([
        {"role": "system", "content": "Sistema"},
        {"role": "user", "content": "primera"},
        {"role": "assistant", "content": "respuesta"},
        {"role": "user", "content": "segunda"},
        {"role": "user", "content": "tercera"},
    ]))
    captured = client.captured[0]
    roles = [c.role for c in captured["contents"]]
    # assistant -> "model"; dos user seguidos se fusionan en uno solo.
    assert roles == ["user", "model", "user"]
    assert len(captured["contents"][2].parts) == 2
    assert captured["contents"][2].parts[0].text == "segunda"
    assert captured["contents"][2].parts[1].text == "tercera"
    assert captured["contents"][0].parts[0].text == "primera"
    assert captured["contents"][1].parts[0].text == "respuesta"


def test_gemini_no_duplica_construccion_de_contexto():
    # El adaptador NO construye contexto: recibe el mensaje único ya armado
    # por ai_service y lo envía tal cual (sin prefijos ni transformaciones).
    client = FakeGeminiClient()
    mensaje_armado = (
        "<conocimiento_oficial_aeternum>...</conocimiento_oficial_aeternum>\n"
        "Pregunta del usuario: Hola"
    )
    _run(_provider(client=client).chat([
        {"role": "system", "content": "Sistema"},
        {"role": "user", "content": mensaje_armado},
    ]))
    received = client.captured[0]["contents"][0].parts[0].text
    assert received == mensaje_armado


# ═══════════════════ 4/14. RESPUESTA VACÍA → ERROR SEGURO ═══════════════════

def test_gemini_respuesta_vacia_contrato_fallido():
    client = FakeGeminiClient(response=FakeGeminiResponse(text=None))
    result = _run(_provider(client=client).chat(
        [{"role": "user", "content": "Hola"}]
    ))
    assert result.success is False
    assert result.text == ""
    assert result.retryable is False


def test_gemini_respuesta_vacia_espacios_contrato_fallido():
    client = FakeGeminiClient(response=FakeGeminiResponse(text="   \n  "))
    result = _run(_provider(client=client).chat(
        [{"role": "user", "content": "Hola"}]
    ))
    assert result.success is False


def test_gemini_respuesta_vacia_error_seguro_en_servicio(fake_db):
    client = FakeGeminiClient(response=FakeGeminiResponse(text=None))
    with pytest.raises(AIServiceError) as excinfo:
        _run(process_chat(
            user=fake_db.state["users"][1], message="Hola",
            provider=_provider(client=client),
        ))
    assert excinfo.value.status_code == 500
    assert "inválida" in excinfo.value.detail


# ═══════════════════ 5/14. TIMEOUT → AIProviderTimeout ══════════════════════

def test_gemini_timeout_mapea_a_ai_provider_timeout():
    client = FakeGeminiClient(exc=httpx.TimeoutException("timeout"))
    provider = _provider(client=client)
    with pytest.raises(AIProviderTimeout) as excinfo:
        _run(provider.chat([{"role": "user", "content": "Hola"}]))
    assert excinfo.value.retryable is True
    assert "GEMINI" not in str(excinfo.value)


def test_gemini_timeout_reintentado_una_vez(fake_db, monkeypatch):
    # Con retry técnico (AI_RETRY_DELAY_MS=0): 1 fallo transitorio + 1 retry
    # exitoso -> 2 llamadas al cliente, respuesta OK.
    monkeypatch.setenv("AI_RETRY_DELAY_MS", "0")
    flaky = FakeGeminiClient()

    class FlakyModels:
        def __init__(self):
            self.owner = flaky

        async def generate_content(self, model=None, contents=None, config=None):
            flaky.calls += 1
            if flaky.calls == 1:
                raise httpx.TimeoutException("timeout")
            return flaky.response

    flaky.aio.models = FlakyModels()
    resp = _run(process_chat(
        user=fake_db.state["users"][1], message="Hola",
        provider=_provider(client=flaky),
    ))
    assert resp["success"] is True
    assert resp["provider"] == "gemini"
    assert flaky.calls == 2


# ═══════════════════ 6/14. ERROR TRANSITORIO → AIProviderUnavailable ════════

def test_gemini_server_error_mapea_a_unavailable():
    exc = genai_errors.ServerError(503, {"error": {"message": "unavailable"}})
    client = FakeGeminiClient(exc=exc)
    with pytest.raises(AIProviderUnavailable) as excinfo:
        _run(_provider(client=client).chat([{"role": "user", "content": "Hola"}]))
    assert excinfo.value.retryable is True


def test_gemini_429_mapea_a_unavailable():
    exc = genai_errors.ClientError(429, {"error": {"message": "rate limit"}})
    client = FakeGeminiClient(exc=exc)
    with pytest.raises(AIProviderUnavailable) as excinfo:
        _run(_provider(client=client).chat([{"role": "user", "content": "Hola"}]))
    assert excinfo.value.retryable is True


def test_gemini_error_red_mapea_a_unavailable():
    client = FakeGeminiClient(exc=httpx.ConnectError("sin conexión"))
    with pytest.raises(AIProviderUnavailable) as excinfo:
        _run(_provider(client=client).chat([{"role": "user", "content": "Hola"}]))
    assert excinfo.value.retryable is True


# ═══════════════════ 7/14. ERROR PERMANENTE → NO RETRYABLE ══════════════════

def test_gemini_error_permanente_4xx_no_retryable():
    exc = genai_errors.ClientError(400, {"error": {"message": "bad request"}})
    client = FakeGeminiClient(exc=exc)
    with pytest.raises(AIProviderError) as excinfo:
        _run(_provider(client=client).chat([{"role": "user", "content": "Hola"}]))
    assert excinfo.value.retryable is False
    assert not isinstance(excinfo.value, AIProviderTimeout)
    assert not isinstance(excinfo.value, AIProviderUnavailable)


def test_gemini_error_permanente_nunca_se_reintenta(fake_db, monkeypatch):
    monkeypatch.setenv("AI_RETRY_DELAY_MS", "0")
    exc = genai_errors.ClientError(400, {"error": {"message": "bad request"}})
    client = FakeGeminiClient(exc=exc)
    with pytest.raises(AIServiceError) as excinfo:
        _run(process_chat(
            user=fake_db.state["users"][1], message="Hola",
            provider=_provider(client=client),
        ))
    assert excinfo.value.status_code == 503
    assert client.calls == 1  # sin reintento


def test_gemini_error_permanente_mensaje_seguro(fake_db):
    exc = genai_errors.ClientError(400, {"error": {"message": "detalle interno"}})
    client = FakeGeminiClient(exc=exc)
    with pytest.raises(AIServiceError) as excinfo:
        _run(process_chat(
            user=fake_db.state["users"][1], message="Hola",
            provider=_provider(client=client),
        ))
    assert "detalle interno" not in excinfo.value.detail
    assert "Gemini" not in excinfo.value.detail


# ═══════════════════ 8/14. NO EXPOSICIÓN DE LA API KEY ══════════════════════

def test_gemini_api_key_nunca_en_mensajes_ni_resultados(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", FAKE_KEY)
    client = FakeGeminiClient()
    provider = _provider(client=client)
    result = _run(provider.chat(
        [{"role": "system", "content": "Sistema"},
         {"role": "user", "content": "Hola"}]
    ))
    assert FAKE_KEY not in result.text
    assert FAKE_KEY not in str(result.usage)
    for entry in client.captured:
        for c in entry["contents"]:
            for part in c.parts:
                assert FAKE_KEY not in part.text
        assert FAKE_KEY not in str(entry["config"])


def test_gemini_api_key_no_va_en_options(monkeypatch, fake_db):
    monkeypatch.setenv("GEMINI_API_KEY", FAKE_KEY)
    client = FakeGeminiClient()

    class CaptureProvider(GeminiAIProvider):
        async def chat(self, messages, options=None):
            self.received_options = options
            return await super().chat(messages, options)

    provider = CaptureProvider(client=client)
    _run(process_chat(
        user=fake_db.state["users"][1], message="Hola", provider=provider,
    ))
    for bad_key in ("token", "cookie", "authorization", "api_key", "secret", "password", "GEMINI_API_KEY"):
        assert bad_key not in provider.received_options
        assert FAKE_KEY not in str(provider.received_options)


def test_gemini_respuesta_endpoint_sin_secretos(monkeypatch, fake_db, as_admin):
    monkeypatch.setenv("GEMINI_API_KEY", FAKE_KEY)
    client = FakeGeminiClient()
    monkeypatch.setattr(
        "ai_service.get_provider", lambda: _provider(client=client),
    )
    resp = as_admin.post("/api/ai/chat", json={"message": "Hola"})
    assert resp.status_code == 200
    body = resp.json()
    # Contrato exacto de respuesta: solo datos seguros y uso numérico.
    assert set(body.keys()) == {
        "success", "message", "provider", "model", "conversation_id", "usage",
    }
    assert body["usage"] == {
        "prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15,
    }
    for secret_fragment in ("api_key", "API_KEY", "GEMINI_API_KEY", FAKE_KEY,
                            "sk-", "Bearer ", "authorization"):
        assert secret_fragment not in str(body)


# ═══════════════════ 9/14. SELECTOR AI_PROVIDER=mock ════════════════════════

def test_selector_mock_sigue_usando_mock(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "mock")
    provider = get_provider()
    assert isinstance(provider, MockAIProvider)
    assert provider.name == "mock"


def test_selector_mock_sin_clave_gemini(monkeypatch):
    # Aunque GEMINI_API_KEY no exista, AI_PROVIDER=mock funciona sin clave.
    monkeypatch.setenv("AI_PROVIDER", "mock")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    assert isinstance(get_provider(), MockAIProvider)


# ═══════════════════ 10/14. SELECTOR AI_PROVIDER=gemini ═════════════════════

def test_selector_gemini_usa_gemini(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", FAKE_KEY)
    provider = get_provider()
    assert isinstance(provider, GeminiAIProvider)
    assert provider.name == "gemini"
    assert provider.model == "gemini-3.6-flash"


def test_selector_gemini_modelo_desde_env(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", FAKE_KEY)
    monkeypatch.setenv("AI_MODEL", "gemini-3.6-flash")
    assert get_provider().model == "gemini-3.6-flash"


# ═══════════════════ 11/14. PROVEEDOR DESCONOCIDO SIGUE FALLANDO ═══════════

def test_proveedor_desconocido_sigue_fallando(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "openai")
    monkeypatch.setenv("GEMINI_API_KEY", FAKE_KEY)
    with pytest.raises(AIProviderConfigError):
        get_provider()


def test_proveedor_desconocido_no_cae_a_mock(monkeypatch, fake_db):
    monkeypatch.setenv("AI_PROVIDER", "openai")
    with pytest.raises(AIServiceError) as excinfo:
        _run(process_chat(user=fake_db.state["users"][1], message="Hola"))
    assert excinfo.value.status_code == 500
    assert "openai" not in excinfo.value.detail


# ═══════════════════ 12/14. RETRY MÁXIMO 1 INTACTO ══════════════════════════

def test_gemini_timeout_persistente_maximo_1_retry(fake_db, monkeypatch):
    monkeypatch.setenv("AI_RETRY_DELAY_MS", "0")

    class TimeoutAlwaysClient(FakeGeminiClient):
        pass

    client = TimeoutAlwaysClient(exc=httpx.TimeoutException("timeout"))
    with pytest.raises(AIServiceError) as excinfo:
        _run(process_chat(
            user=fake_db.state["users"][1], message="Hola",
            provider=_provider(client=client),
        ))
    assert excinfo.value.status_code == 503
    assert "tardó demasiado" in excinfo.value.detail
    assert client.calls == 2  # exactamente 2 intentos, nunca más


def test_gemini_unavailable_persistente_maximo_1_retry(fake_db, monkeypatch):
    monkeypatch.setenv("AI_RETRY_DELAY_MS", "0")
    exc = genai_errors.ServerError(503, {"error": {"message": "unavailable"}})
    client = FakeGeminiClient(exc=exc)
    with pytest.raises(AIServiceError) as excinfo:
        _run(process_chat(
            user=fake_db.state["users"][1], message="Hola",
            provider=_provider(client=client),
        ))
    assert excinfo.value.status_code == 503
    assert client.calls == 2


def test_gemini_retry_contrato_excepciones():
    # El adaptador reutiliza el contrato FASE 8.8: timeout y no disponible
    # son transitorios por defecto; permanente NO.
    assert AIProviderTimeout("x").retryable is True
    assert AIProviderUnavailable("x").retryable is True
    assert AIProviderError("x").retryable is False


# ═══════════════════ 13/14. ECONOMÍA SIGUE DESACTIVADA ══════════════════════

def test_economia_sigue_desactivada_con_gemini(monkeypatch):
    monkeypatch.delenv("AI_ECONOMY_ENABLED", raising=False)
    monkeypatch.setenv("AI_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", FAKE_KEY)
    # Seleccionar Gemini NO activa la economía.
    assert ai_rayos.is_economy_active() is False
    assert ai_rayos.AI_COST_CHAT is None
    assert ai_rayos.get_operation_cost("chat") is None
    assert ai_rayos.estimate_operation_cost("chat") is None


def test_gemini_exitoso_sin_cobro(monkeypatch, fake_db):
    monkeypatch.setenv("AI_RETRY_DELAY_MS", "0")
    client = FakeGeminiClient()
    saldo = fake_db.state["users"][1]["rayos_balance"]
    resp = _run(process_chat(
        user=fake_db.state["users"][1], message="Hola",
        provider=_provider(client=client), db=fake_db,
    ))
    assert resp["success"] is True
    assert fake_db.state["users"][1]["rayos_balance"] == saldo
    assert fake_db.state["ai_consumption"] == []
    assert fake_db.state["rayos_transactions"] == []


# ═══════════════════ 14/14. PERSISTENCIA Y CONTEXTO SIGUEN FUNCIONANDO ═════

def test_gemini_persistencia_y_contexto_en_servicio(fake_db):
    client = FakeGeminiClient()
    resp = _run(process_chat(
        user=fake_db.state["users"][1], message="Hola",
        provider=_provider(client=client), db=fake_db,
    ))
    assert resp["success"] is True
    assert resp["provider"] == "gemini"
    assert isinstance(resp["conversation_id"], int)
    # user + assistant persistidos en orden.
    msgs = [
        m for m in fake_db.state["ai_messages"]
        if m["conversation_id"] == resp["conversation_id"]
    ]
    assert [m["role"] for m in msgs] == ["user", "assistant"]
    assert msgs[0]["content"] == "Hola"
    assert msgs[1]["content"] == "Respuesta de prueba de Gemini"
    # El mensaje enviado a Gemini es el contexto ya construido por ai_service
    # (oficial + pregunta), sin duplicar construcción en el adaptador.
    captured = client.captured[0]
    user_content = captured["contents"][0].parts[0].text
    assert "<conocimiento_oficial_aeternum>" in user_content
    assert "Pregunta del usuario: Hola" in user_content
    assert captured["config"].system_instruction
    assert "Aeternum" in captured["config"].system_instruction


def test_gemini_contexto_de_libro_no_duplicado(fake_db):
    client = FakeGeminiClient()
    _run(process_chat(
        user=fake_db.state["users"][3],
        message="¿Qué significa esta página?",
        book_id=10,
        page_number=1,
        provider=_provider(client=client),
        can_access_book=server._puede_acceder_libro,
        db=fake_db,
    ))
    captured = client.captured[0]
    user_content = captured["contents"][0].parts[0].text
    assert "<datos_libro>" in user_content
    assert "página del libro publicado" in user_content
    # La pregunta viaja una sola vez, al final (no se duplica el contexto).
    assert user_content.count("Pregunta del usuario:") == 1
    roles = [c.role for c in captured["contents"]]
    assert roles == ["user"]  # system -> system_instruction, no en contents


# ═══════════ 15/14. CICLO DE VIDA DEL CLIENTE (FASE 8.14.2) ═════════════════

def test_gemini_cliente_inyectado_no_se_cierra(fake_db):
    # Regla FASE 8.14.2: un cliente inyectado (tests) NUNCA se cierra.
    client = FakeGeminiClient()
    resp = _run(process_chat(
        user=fake_db.state["users"][1], message="Hola",
        provider=_provider(client=client),
    ))
    assert resp["success"] is True
    assert client.calls == 1
    assert client.aclose_calls == 0
    assert client.close_calls == 0


def test_gemini_cliente_inyectado_no_se_cierra_en_error(fake_db):
    client = FakeGeminiClient(exc=httpx.TimeoutException("timeout"))
    with pytest.raises(AIServiceError):
        _run(process_chat(
            user=fake_db.state["users"][1], message="Hola",
            provider=_provider(client=client),
        ))
    assert client.aclose_calls == 0
    assert client.close_calls == 0


def test_gemini_cliente_creado_por_adaptador_se_limpia(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", FAKE_KEY)
    owned = FakeGeminiClient()
    monkeypatch.setattr(GeminiAIProvider, "_build_client", lambda self: owned)
    provider = GeminiAIProvider()
    result = _run(provider.chat([{"role": "user", "content": "Hola"}]))
    assert result.success is True
    assert owned.calls == 1
    # Ciclo de vida controlado: se cierra el cliente async (aclose) y el
    # sync (close) exactamente una vez.
    assert owned.aclose_calls == 1
    assert owned.close_calls == 1


def test_gemini_cliente_creado_por_adaptador_se_limpia_en_timeout(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", FAKE_KEY)
    owned = FakeGeminiClient(exc=httpx.TimeoutException("timeout"))
    monkeypatch.setattr(GeminiAIProvider, "_build_client", lambda self: owned)
    provider = GeminiAIProvider()
    with pytest.raises(AIProviderTimeout):
        _run(provider.chat([{"role": "user", "content": "Hola"}]))
    # El cierre también ocurre en la ruta de error (finally).
    assert owned.aclose_calls == 1
    assert owned.close_calls == 1


def test_gemini_cliente_creado_por_adaptador_no_se_cerro_en_construccion(monkeypatch):
    # FASE 8.14.2: el adaptador ya NO crea el cliente en __init__; la
    # construcción solo valida configuración (clave ausente -> error).
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(AIProviderConfigError):
        GeminiAIProvider()
    monkeypatch.setenv("GEMINI_API_KEY", FAKE_KEY)
    provider = GeminiAIProvider()
    assert provider._owns_client is True
    assert provider._client is None


def test_gemini_cliente_propio_por_intento_con_retry(fake_db, monkeypatch):
    # Retry técnico (FASE 8.8, máximo 1): cada intento usa un cliente propio
    # nuevo y se cierra al terminar; el reintento funciona sobre un cliente
    # limpio (nunca un cliente cerrado).
    monkeypatch.setenv("GEMINI_API_KEY", FAKE_KEY)
    monkeypatch.setenv("AI_RETRY_DELAY_MS", "0")
    clients = []

    def factory(self):
        client = FakeGeminiClient()
        clients.append(client)
        if len(clients) == 1:
            client.exc = httpx.TimeoutException("timeout")
        return client

    monkeypatch.setattr(GeminiAIProvider, "_build_client", factory)
    provider = GeminiAIProvider()
    resp = _run(process_chat(
        user=fake_db.state["users"][1], message="Hola", provider=provider,
    ))
    assert resp["success"] is True
    assert len(clients) == 2  # 1 fallo transitorio + 1 reintento exitoso
    for client in clients:
        assert client.aclose_calls == 1
        assert client.close_calls == 1


def test_gemini_cliente_creado_por_adaptador_uso_por_llamada(monkeypatch):
    # Una misma instancia del adaptador con cliente propio usa UN cliente
    # distinto por llamada chat() (sin estado compartido entre llamadas).
    monkeypatch.setenv("GEMINI_API_KEY", FAKE_KEY)
    clients = []
    monkeypatch.setattr(
        GeminiAIProvider, "_build_client", lambda self: clients.append(
            FakeGeminiClient()
        ) or clients[-1],
    )
    provider = GeminiAIProvider()
    _run(provider.chat([{"role": "user", "content": "primera"}]))
    _run(provider.chat([{"role": "user", "content": "segunda"}]))
    assert len(clients) == 2
    assert all(c.aclose_calls == 1 and c.close_calls == 1 for c in clients)