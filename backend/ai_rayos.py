"""Integración económica de IA en Rayos (FASE 8.5).

ESTADO POR DEFECTO: INACTIVA. La economía solo se activa con configuración
explícita (AI_ECONOMY_ENABLED), INDEPENDIENTE de AI_PROVIDER. Con costos
PENDIENTES de confirmación comercial, aunque se active la economía nunca se
cobra (status no_charge): NO se crea dinero artificial.

REGLAS DE LA FASE:
  - PUNTO DE COBRO: SOLO después de una respuesta VÁLIDA del proveedor.
    Si el proveedor falla, hace timeout, devuelve error, respuesta vacía o
    formato inválido -> NO SE COBRA. No es un reembolso: simplemente no se
    realiza el débito.
  - PRE-CHEQUEO DE SALDO sin reserva: se consulta el saldo ANTES de llamar
    al proveedor (lectura simple, no bloquea nada) para no gastar una
    llamada si el usuario no puede pagar. El débito real es atómico y
    posterior a la respuesta válida. Esto NO es una reserva de Rayos.
  - SALDO NUNCA NEGATIVO: se reutiliza _debit_rayos_atomic (UPDATE condicional
    con RETURNING), el mismo helper de todo el sistema de Rayos.
  - historical_rayos NO se toca: _debit_rayos_atomic solo descuenta
    rayos_balance; los débitos de IA nunca disminuyen el histórico.
  - IDEMPOTENCIA: operation_id UNIQUE en ai_consumption. Una solicitud
    económica se cobra UNA sola vez por operation_id (retries, doble submit
    o concurrencia no generan doble cobro).

CONTRATO charge_operation(...) -> dict normalizado:
  {"status": "charged",               "operation_id", "rayos_cost", "balance_after"}
  {"status": "no_charge",             ...}   sin costo definido (precios PENDIENTES)
  {"status": "inactive",              ...}   economía desactivada
  {"status": "insufficient_balance",  ...}   saldo insuficiente en el débito atómico
  {"status": "already_processed",     ...}   operation_id ya cobrado (mismo usuario)
  {"status": "rejected",              ...}   operation_id pertenece a OTRO usuario

ai_service.py no conoce SQL ni detalles internos de Rayos: solo llama a esta
capa y recibe resultados normalizados.
"""

import os
import uuid
from datetime import datetime, timezone

# Costos PENDIENTES de confirmación comercial. NO seleccionados:
#   300 Rayos/7 días vs 900 Rayos/30 días vs 600 Rayos/7 días vs 1800/30.
# get_operation_cost devuelve None -> la economía nunca cobra sin precio
# definido, aunque esté activada por configuración.
AI_COST_CHAT = None  # PENDIENTE: costo por operación de chat (sin valor activo)


def _env_bool(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


def is_economy_active():
    """La economía de IA se activa SOLO con configuración explícita.

    Independiente de AI_PROVIDER: tener proveedor configurado NO activa la
    economía. AI_ECONOMY_ENABLED=1 la activa; ausente o "0" -> inactiva.
    """
    return _env_bool("AI_ECONOMY_ENABLED")


def get_operation_cost(operation, context=None):
    """Costo de una operación de IA.

    FASE 8.5: PENDIENTE de confirmación comercial -> devuelve None. Con None,
    charge_operation responde no_charge y NO se descuenta nada.
    """
    if operation == "chat":
        return AI_COST_CHAT
    return None


def estimate_operation_cost(operation, context=None):
    """Estimación de costo de una operación de IA (hook FASE 8.3/8.4).

    Sin valores comerciales definidos, estimar == None (no-op).
    """
    return get_operation_cost(operation, context)


def precheck_balance(db, user_id, cost):
    """Pre-chequeo de saldo SIN reserva (FASE 8.5, sección 9).

    Lectura simple del saldo antes de llamar al proveedor: si el usuario no
    puede pagar, se rechaza sin gastar una llamada de IA. NO bloquea saldo,
    NO descuenta nada: el débito real es atómico y posterior a la respuesta
    válida (punto de cobro oficial de esta fase).
    """
    if cost is None or cost <= 0:
        return True
    cursor = db.cursor()
    cursor.execute("SELECT rayos_balance FROM users WHERE id = %s", (user_id,))
    row = cursor.fetchone()
    return row is not None and row["rayos_balance"] >= cost


def charge_operation(db, user_id, operation_id, operation, cost,
                     provider=None, model=None, duration_ms=None):
    """Operación económica de una solicitud de IA (punto de cobro).

    Se llama SOLO después de una respuesta VÁLIDA del proveedor. Gestiona su
    propia transacción (commit/rollback) y reutiliza _debit_rayos_atomic.

    Resultado normalizado: charged | no_charge | inactive |
    insufficient_balance | already_processed | rejected.
    """
    if not is_economy_active():
        return {"status": "inactive"}

    if cost is None or cost <= 0:
        # Precios PENDIENTES: sin costo definido NO se cobra nunca.
        return {"status": "no_charge"}

    if not operation_id:
        # El cliente no envió clave de idempotencia: el servidor genera una
        # interna para poder registrar la operación sin duplicación.
        operation_id = str(uuid.uuid4())

    cursor = db.cursor()

    # Import tardío: server.py importa ai_service -> ai_rayos; se evita el
    # ciclo de importación cargando el helper económico solo al usarlo.
    from server import _debit_rayos_atomic

    # 1. IDEMPOTENCIA: la operación ya fue procesada con este operation_id?
    cursor.execute(
        "SELECT id, user_id, status FROM ai_consumption WHERE operation_id = %s",
        (operation_id,),
    )
    existing = cursor.fetchone()
    if existing:
        if existing["user_id"] != user_id:
            # El operation_id pertenece a otro usuario: NUNCA se expone ni se
            # permite gastar Rayos de nadie más.
            return {"status": "rejected", "operation_id": operation_id}
        return {"status": "already_processed", "operation_id": operation_id}

    # 2. DÉBITO ATÓMICO (helper existente de todo el sistema de Rayos):
    #    UPDATE condicional -> saldo nunca negativo; no toca historical_rayos.
    new_balance = _debit_rayos_atomic(
        cursor,
        user_id,
        cost,
        "ai_request_cost",
        f"Costo de operación de IA ({operation})",
    )
    if new_balance is None:
        return {"status": "insufficient_balance", "operation_id": operation_id}

    # 3. REGISTRO DE CONSUMO en la misma transacción (atomicidad: no puede
    #    existir "cobro sin registro" ni "registro sin cobro").
    now = datetime.now(timezone.utc).isoformat()
    try:
        cursor.execute(
            """
            INSERT INTO ai_consumption
                (user_id, operation_id, operation, provider, model,
                 rayos_cost, status, duration_ms, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                user_id,
                operation_id,
                operation,
                provider,
                model,
                cost,
                "success",
                duration_ms,
                now,
            ),
        )
    except Exception as exc:
        # CARRERA DE CONCURRENCIA: otra solicitud simultánea con el mismo
        # operation_id ganó el INSERT (violación de UNIQUE, pgcode 23505 en
        # PostgreSQL). Se deshace el débito de esta transacción (rollback) y
        # se reporta como ya procesada: NO puede haber doble cobro.
        if getattr(exc, "pgcode", None) != "23505":
            raise
        db.rollback()
        return {"status": "already_processed", "operation_id": operation_id}

    db.commit()
    return {
        "status": "charged",
        "operation_id": operation_id,
        "rayos_cost": cost,
        "balance_after": new_balance,
    }


def refund_operation(db, user_id, operation_id, context=None):
    """Reembolso puntual de una operación de IA.

    FASE 8.5: NO implementado y NO necesario. La política declarada es
    "NO COBRAR una solicitud que no haya producido una respuesta válida":
    si el proveedor falla, no existe débito que reembolsar. No se crean
    refunds como mecánica ficticia.
    """
    return None