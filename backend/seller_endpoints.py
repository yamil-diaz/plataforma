# seller_endpoints.py — Endpoints para Seller Platform (FASE 2.3)
# Agregar estos endpoints a server.py

from fastapi import APIRouter, Depends, HTTPException
from decimal import Decimal
from database import get_db
from commerce_seller_service import (
    get_seller_dashboard,
    create_payout_request,
    get_seller_payouts,
)

router = APIRouter(prefix="/api/seller", tags=["seller"])


# Middleware: verificar que el usuario es vendedor aprobado
def verify_seller(token: dict = Depends(verify_token)) -> dict:
    """Verifica que el usuario es vendedor verificado."""
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute(
        "SELECT id, seller_verified FROM users WHERE id = %s",
        (token["user_id"],),
    )
    user = cursor.fetchone()
    db.close()
    
    if not user or not user["seller_verified"]:
        raise HTTPException(status_code=403, detail="Not an approved seller")
    
    return {**token, "seller_verified": True}


@router.get("/dashboard")
def get_seller_dashboard_endpoint(token: dict = Depends(verify_seller)):
    """Dashboard de vendedor con estadísticas, comisiones y balance."""
    db = get_db()
    cursor = db.cursor()
    result = get_seller_dashboard(cursor, token["user_id"])
    db.close()
    
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Error"))
    
    return result


@router.post("/payout/request")
def request_payout_endpoint(
    amount: Decimal,
    currency: str = "PEN",
    payment_method: str = "bank_transfer",
    token: dict = Depends(verify_seller)
):
    """Solicita un payout de comisiones."""
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")
    
    db = get_db()
    cursor = db.cursor()
    
    try:
        result = create_payout_request(cursor, token["user_id"], amount, currency, payment_method)
        db.commit()
        db.close()
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Error"))
        
        return result
    except Exception as e:
        db.rollback()
        db.close()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/payouts")
def get_seller_payouts_endpoint(token: dict = Depends(verify_seller)):
    """Historial de payouts del vendedor."""
    db = get_db()
    cursor = db.cursor()
    result = get_seller_payouts(cursor, token["user_id"])
    db.close()
    
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Error"))
    
    return result


@router.get("/commissions")
def get_seller_commissions(token: dict = Depends(verify_seller), limit: int = 50):
    """Historial de comisiones del vendedor."""
    db = get_db()
    cursor = db.cursor()
    
    try:
        cursor.execute(
            """SELECT sc.id, sc.order_id, sc.book_id, sc.commission_amount, sc.currency, sc.status, sc.created_at,
               b.title as book_title, o.order_number
               FROM seller_commissions sc
               LEFT JOIN books b ON sc.book_id = b.id
               LEFT JOIN orders o ON sc.order_id = o.id
               WHERE sc.seller_id = %s
               ORDER BY sc.created_at DESC
               LIMIT %s""",
            (token["user_id"], limit),
        )
        commissions = cursor.fetchall()
        db.close()
        
        return {"success": True, "commissions": commissions}
    except Exception as e:
        db.close()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/books")
def get_seller_books(token: dict = Depends(verify_seller)):
    """Libros del vendedor con comisiones."""
    db = get_db()
    cursor = db.cursor()
    
    try:
        cursor.execute(
            """SELECT id, title, author_name, price, commission_percentage, is_for_sale, created_at
               FROM books
               WHERE seller_id = %s
               ORDER BY created_at DESC""",
            (token["user_id"],),
        )
        books = cursor.fetchall()
        db.close()
        
        return {"success": True, "books": books}
    except Exception as e:
        db.close()
        raise HTTPException(status_code=500, detail=str(e))


# ADMIN ENDPOINTS

@router.get("/admin/applications")
def admin_list_seller_applications(token: dict = Depends(verify_token)):
    """Admin: Listar solicitudes de vendedor (requiere rol admin)."""
    db = get_db()
    cursor = db.cursor()
    
    # Verificar admin
    cursor.execute("SELECT role FROM users WHERE id = %s", (token["user_id"],))
    user = cursor.fetchone()
    if not user or user["role"] != "admin":
        db.close()
        raise HTTPException(status_code=403, detail="Admin only")
    
    try:
        cursor.execute(
            """SELECT sa.id, sa.user_id, sa.business_name, sa.business_type, sa.status, 
               sa.created_at, sa.reviewed_at, u.email, u.name
               FROM seller_applications sa
               LEFT JOIN users u ON sa.user_id = u.id
               ORDER BY sa.created_at DESC"""
        )
        apps = cursor.fetchall()
        db.close()
        
        return {"success": True, "applications": apps}
    except Exception as e:
        db.close()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/admin/approve/{app_id}")
def admin_approve_seller(app_id: int, note: str = "", token: dict = Depends(verify_token)):
    """Admin: Aprobar solicitud de vendedor."""
    db = get_db()
    cursor = db.cursor()
    
    # Verificar admin
    cursor.execute("SELECT role FROM users WHERE id = %s", (token["user_id"],))
    user = cursor.fetchone()
    if not user or user["role"] != "admin":
        db.close()
        raise HTTPException(status_code=403, detail="Admin only")
    
    try:
        now = datetime.now(timezone.utc).isoformat()
        
        cursor.execute(
            """UPDATE seller_applications
               SET status = 'approved', admin_note = %s, reviewed_by = %s, reviewed_at = %s
               WHERE id = %s
               RETURNING user_id""",
            (note, token["user_id"], now, app_id),
        )
        row = cursor.fetchone()
        if not row:
            db.close()
            raise HTTPException(status_code=404, detail="Application not found")
        
        seller_id = row["user_id"]
        
        # Actualizar usuario
        cursor.execute(
            """UPDATE users
               SET seller_verified = TRUE, seller_approved_at = %s
               WHERE id = %s""",
            (now, seller_id),
        )
        
        # Crear saldo inicial
        cursor.execute(
            """INSERT INTO seller_balances (seller_id, currency, total_earned, pending_amount, updated_at)
               VALUES (%s, 'PEN', 0, 0, %s)
               ON CONFLICT DO NOTHING""",
            (seller_id, now),
        )
        
        db.commit()
        db.close()
        
        return {"success": True, "message": "Seller approved"}
    except Exception as e:
        db.rollback()
        db.close()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/admin/reject/{app_id}")
def admin_reject_seller(app_id: int, reason: str = "", token: dict = Depends(verify_token)):
    """Admin: Rechazar solicitud de vendedor."""
    db = get_db()
    cursor = db.cursor()
    
    # Verificar admin
    cursor.execute("SELECT role FROM users WHERE id = %s", (token["user_id"],))
    user = cursor.fetchone()
    if not user or user["role"] != "admin":
        db.close()
        raise HTTPException(status_code=403, detail="Admin only")
    
    try:
        now = datetime.now(timezone.utc).isoformat()
        
        cursor.execute(
            """UPDATE seller_applications
               SET status = 'rejected', admin_note = %s, reviewed_by = %s, reviewed_at = %s
               WHERE id = %s""",
            (reason, token["user_id"], now, app_id),
        )
        
        db.commit()
        db.close()
        
        return {"success": True, "message": "Seller rejected"}
    except Exception as e:
        db.rollback()
        db.close()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/admin/payouts")
def admin_list_payouts(token: dict = Depends(verify_token)):
    """Admin: Listar todos los payouts (requiere rol admin)."""
    db = get_db()
    cursor = db.cursor()
    
    # Verificar admin
    cursor.execute("SELECT role FROM users WHERE id = %s", (token["user_id"],))
    user = cursor.fetchone()
    if not user or user["role"] != "admin":
        db.close()
        raise HTTPException(status_code=403, detail="Admin only")
    
    try:
        cursor.execute(
            """SELECT sp.id, sp.payout_number, sp.amount, sp.currency, sp.status, 
               sp.payment_method, sp.created_at, sp.completed_at,
               u.email, u.name
               FROM seller_payouts sp
               LEFT JOIN users u ON sp.seller_id = u.id
               ORDER BY sp.created_at DESC"""
        )
        payouts = cursor.fetchall()
        db.close()
        
        return {"success": True, "payouts": payouts}
    except Exception as e:
        db.close()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/admin/payout/{payout_id}/complete")
def admin_complete_payout(payout_id: int, transaction_id: str = "", token: dict = Depends(verify_token)):
    """Admin: Marcar payout como completado."""
    db = get_db()
    cursor = db.cursor()
    
    # Verificar admin
    cursor.execute("SELECT role FROM users WHERE id = %s", (token["user_id"],))
    user = cursor.fetchone()
    if not user or user["role"] != "admin":
        db.close()
        raise HTTPException(status_code=403, detail="Admin only")
    
    try:
        now = datetime.now(timezone.utc).isoformat()
        
        cursor.execute(
            """UPDATE seller_payouts
               SET status = 'completed', transaction_id = %s, completed_at = %s, processed_at = %s
               WHERE id = %s
               RETURNING seller_id, amount, currency""",
            (transaction_id, now, now, payout_id),
        )
        row = cursor.fetchone()
        if not row:
            db.close()
            raise HTTPException(status_code=404, detail="Payout not found")
        
        seller_id = row["seller_id"]
        amount = row["amount"]
        currency = row["currency"]
        
        # Actualizar balance
        cursor.execute(
            """UPDATE seller_balances
               SET total_paid = total_paid + %s, updated_at = %s
               WHERE seller_id = %s AND currency = %s""",
            (amount, now, seller_id, currency),
        )
        
        db.commit()
        db.close()
        
        return {"success": True, "message": "Payout completed"}
    except Exception as e:
        db.rollback()
        db.close()
        raise HTTPException(status_code=500, detail=str(e))

# ────────────────────────────────────────────────────────────────────────────
# EN server.py, AGREGAR ESTO DESPUÉS DE INICIALIZAR FastAPI:
#
# from seller_endpoints import router as seller_router
# app.include_router(seller_router)
# ────────────────────────────────────────────────────────────────────────────
