"""
Endpoints del sistema de vendedores para AeternumLibrary.
Integrar estos endpoints en server.py después de la línea 1677.
"""

# ── Modelos Pydantic ──────────────────────────────────────────────────────

class SellerApplicationRequest(BaseModel):
    business_name: str
    business_type: str  # "individual", "company"
    tax_id: Optional[str] = None
    phone: str
    address: str
    city: str
    country: str = "Perú"
    description: str


# ── Solicitud de vendedor (usuario comprador) ──────────────────────────────

@api_router.post("/seller/apply")
async def apply_to_be_seller(req: SellerApplicationRequest, request: Request):
    """Usuario comprador solicita convertirse en vendedor."""
    user = await get_current_user(request)
    
    # Solo compradores pueden solicitar ser vendedores
    if user["role"] not in ("buyer", "user"):  # user por compatibilidad legacy
        raise HTTPException(status_code=400, detail="Solo los compradores pueden solicitar ser vendedores")
    
    db = get_db()
    cursor = db.cursor()
    try:
        # Verificar si ya existe una solicitud pendiente o aprobada
        cursor.execute(
            "SELECT id, status FROM seller_applications WHERE user_id = %s",
            (user["id"],)
        )
        existing = cursor.fetchone()
        
        if existing:
            if existing["status"] == "pending":
                raise HTTPException(status_code=400, detail="Ya tienes una solicitud pendiente de revisión")
            elif existing["status"] == "approved":
                raise HTTPException(status_code=400, detail="Ya eres vendedor verificado")
            elif existing["status"] == "rejected":
                # Permitir reaplicar si fue rechazado
                cursor.execute(
                    """UPDATE seller_applications SET
                       business_name = %s, business_type = %s, tax_id = %s, phone = %s,
                       address = %s, city = %s, country = %s, description = %s,
                       status = 'pending', admin_note = NULL, reviewed_by = NULL, reviewed_at = NULL,
                       created_at = %s
                       WHERE user_id = %s""",
                    (req.business_name, req.business_type, req.tax_id, req.phone,
                     req.address, req.city, req.country, req.description,
                     datetime.now(timezone.utc).isoformat(), user["id"])
                )
        else:
            # Nueva solicitud
            cursor.execute(
                """INSERT INTO seller_applications
                   (user_id, business_name, business_type, tax_id, phone, address, city, country, description, created_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (user["id"], req.business_name, req.business_type, req.tax_id, req.phone,
                 req.address, req.city, req.country, req.description,
                 datetime.now(timezone.utc).isoformat())
            )
        
        db.commit()
        
        # Notificar a admins
        cursor.execute("SELECT id FROM users WHERE role = 'admin'")
        admin_ids = [row["id"] for row in cursor.fetchall()]
        now = datetime.now(timezone.utc).isoformat()
        for admin_id in admin_ids:
            cursor.execute(
                """INSERT INTO notifications (user_id, type, content, created_at)
                   VALUES (%s, 'seller_application', %s, %s)""",
                (admin_id, f"Nueva solicitud de vendedor de {user['name']}", now)
            )
        db.commit()
        
        return {"message": "Solicitud enviada correctamente. Te notificaremos cuando sea revisada."}
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al procesar solicitud: {str(e)}")
    finally:
        db.close()


@api_router.get("/seller/application/status")
async def get_seller_application_status(request: Request):
    """Consultar estado de la solicitud de vendedor del usuario actual."""
    user = await get_current_user(request)
    
    db = get_db()
    cursor = db.cursor()
    try:
        cursor.execute(
            "SELECT * FROM seller_applications WHERE user_id = %s",
            (user["id"],)
        )
        app = cursor.fetchone()
        
        if not app:
            return {"has_application": False}
        
        return {
            "has_application": True,
            "status": app["status"],
            "created_at": app["created_at"],
            "reviewed_at": app["reviewed_at"],
            "admin_note": app["admin_note"] if app["status"] == "rejected" else None
        }
    finally:
        db.close()


# ── Panel admin: gestión de solicitudes de vendedor ────────────────────────

@api_router.get("/admin/seller-applications")
async def admin_list_seller_applications(status: str = None, request: Request = None):
    """Listar solicitudes de vendedor. Solo admin."""
    user = await get_current_user(request)
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="No autorizado")
    
    db = get_db()
    cursor = db.cursor()
    try:
        query = """
            SELECT sa.*, u.name as user_name, u.email as user_email
            FROM seller_applications sa
            JOIN users u ON u.id = sa.user_id
        """
        params = []
        
        if status and status in ("pending", "approved", "rejected"):
            query += " WHERE sa.status = %s"
            params.append(status)
        
        query += " ORDER BY sa.created_at DESC"
        
        cursor.execute(query, params if params else None)
        applications = cursor.fetchall()
        
        return [dict(row) for row in applications]
        
    finally:
        db.close()


class ReviewSellerApplicationRequest(BaseModel):
    application_id: int
    action: str  # "approve" or "reject"
    admin_note: Optional[str] = None


@api_router.post("/admin/seller-applications/review")
async def admin_review_seller_application(req: ReviewSellerApplicationRequest, request: Request):
    """Aprobar o rechazar solicitud de vendedor. Solo admin."""
    user = await get_current_user(request)
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="No autorizado")
    
    if req.action not in ("approve", "reject"):
        raise HTTPException(status_code=400, detail="Acción inválida")
    
    db = get_db()
    cursor = db.cursor()
    try:
        # Obtener solicitud
        cursor.execute(
            "SELECT * FROM seller_applications WHERE id = %s",
            (req.application_id,)
        )
        app = cursor.fetchone()
        
        if not app:
            raise HTTPException(status_code=404, detail="Solicitud no encontrada")
        
        if app["status"] != "pending":
            raise HTTPException(status_code=400, detail="La solicitud ya fue revisada")
        
        now = datetime.now(timezone.utc).isoformat()
        new_status = "approved" if req.action == "approve" else "rejected"
        
        # Actualizar solicitud
        cursor.execute(
            """UPDATE seller_applications
               SET status = %s, admin_note = %s, reviewed_by = %s, reviewed_at = %s
               WHERE id = %s""",
            (new_status, req.admin_note, user["id"], now, req.application_id)
        )
        
        # Si se aprueba, actualizar usuario a seller
        if req.action == "approve":
            cursor.execute(
                """UPDATE users
                   SET role = 'seller', seller_verified = TRUE, seller_approved_at = %s
                   WHERE id = %s""",
                (now, app["user_id"])
            )
        
        # Crear notificación para el solicitante
        if req.action == "approve":
            notif_content = "¡Felicitaciones! Tu solicitud para ser vendedor ha sido aprobada. Ahora puedes publicar y vender libros en la plataforma."
        else:
            notif_content = f"Tu solicitud para ser vendedor ha sido rechazada. {req.admin_note or 'Contacta a soporte para más información.'}"
        
        cursor.execute(
            """INSERT INTO notifications (user_id, type, content, created_at)
               VALUES (%s, 'seller_review', %s, %s)""",
            (app["user_id"], notif_content, now)
        )
        
        db.commit()
        
        # Enviar email
        cursor.execute("SELECT name, email FROM users WHERE id = %s", (app["user_id"],))
        applicant = cursor.fetchone()
        
        if applicant:
            subject = "Solicitud de vendedor aprobada" if req.action == "approve" else "Solicitud de vendedor rechazada"
            
            if req.action == "approve":
                html = f"""
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; padding: 20px;">
                    <div style="text-align: center; margin-bottom: 20px;">
                        <h1 style="color: #D92B2B; margin: 0;">AETERNUM</h1>
                    </div>
                    <div style="background: #1a1a1a; border-radius: 12px; padding: 30px; color: white;">
                        <h2 style="color: #10B981; margin-top: 0;">¡Solicitud Aprobada!</h2>
                        <p>Hola {applicant["name"]},</p>
                        <p>Nos complace informarte que tu solicitud para ser vendedor en AETERNUM ha sido aprobada.</p>
                        <p>Ahora puedes:</p>
                        <ul>
                            <li>Publicar libros digitales y físicos</li>
                            <li>Gestionar tus ventas</li>
                            <li>Acceder a tu panel de vendedor</li>
                        </ul>
                        <a href="https://aeternumlibrary.com/dashboard" style="display: inline-block; padding: 12px 24px; background-color: #D92B2B; color: white; text-decoration: none; border-radius: 8px; font-weight: bold; margin-top: 15px;">Ir a mi Panel</a>
                    </div>
                </div>
                """
            else:
                html = f"""
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; padding: 20px;">
                    <div style="text-align: center; margin-bottom: 20px;">
                        <h1 style="color: #D92B2B; margin: 0;">AETERNUM</h1>
                    </div>
                    <div style="background: #1a1a1a; border-radius: 12px; padding: 30px; color: white;">
                        <h2 style="color: #EF4444; margin-top: 0;">Solicitud Rechazada</h2>
                        <p>Hola {applicant["name"]},</p>
                        <p>Lamentamos informarte que tu solicitud para ser vendedor no ha sido aprobada en este momento.</p>
                        {f'<p><strong>Motivo:</strong> {req.admin_note}</p>' if req.admin_note else ''}
                        <p>Puedes volver a aplicar cuando cumplas con los requisitos necesarios.</p>
                        <a href="https://aeternumlibrary.com" style="display: inline-block; padding: 12px 24px; background-color: #D92B2B; color: white; text-decoration: none; border-radius: 8px; font-weight: bold; margin-top: 15px;">Volver a la Plataforma</a>
                    </div>
                </div>
                """
            
            try:
                send_email_async(applicant["email"], subject, html)
            except Exception as e:
                print(f"Error enviando email: {e}")
        
        return {"message": f"Solicitud {'aprobada' if req.action == 'approve' else 'rechazada'} correctamente"}
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al revisar solicitud: {str(e)}")
    finally:
        db.close()


# ── Panel de ventas para vendedores ─────────────────────────────────────────

@api_router.get("/seller/sales")
async def get_seller_sales(request: Request):
    """Obtener ventas del vendedor actual."""
    user = await get_current_user(request)
    
    if user["role"] != "seller":
        raise HTTPException(status_code=403, detail="Solo vendedores pueden acceder a esta información")
    
    db = get_db()
    cursor = db.cursor()
    try:
        # Obtener ventas de libros del vendedor
        cursor.execute("""
            SELECT o.id, o.order_number, o.order_type, o.currency, o.total, o.created_at, o.payment_status,
                   b.title as book_title, u.name as buyer_name, u.email as buyer_email
            FROM orders o
            JOIN order_items oi ON oi.order_id = o.id
            JOIN books b ON b.id = oi.book_id
            JOIN users u ON u.id = o.user_id
            WHERE b.uploader_id = %s AND o.payment_status = 'approved'
            ORDER BY o.created_at DESC
        """, (user["id"],))
        
        sales = cursor.fetchall()
        
        # Calcular estadísticas
        cursor.execute("""
            SELECT COUNT(*) as total_sales,
                   SUM(o.total) as total_revenue,
                   COUNT(DISTINCT o.user_id) as unique_buyers
            FROM orders o
            JOIN order_items oi ON oi.order_id = o.id
            JOIN books b ON b.id = oi.book_id
            WHERE b.uploader_id = %s AND o.payment_status = 'approved'
        """, (user["id"],))
        
        stats = cursor.fetchone()
        
        return {
            "sales": [dict(row) for row in sales],
            "stats": {
                "total_sales": stats["total_sales"] or 0,
                "total_revenue": float(stats["total_revenue"] or 0),
                "unique_buyers": stats["unique_buyers"] or 0
            }
        }
        
    finally:
        db.close()


# ── Panel de compras para compradores ───────────────────────────────────────

@api_router.get("/buyer/purchases")
async def get_buyer_purchases(request: Request):
    """Obtener compras del comprador actual."""
    user = await get_current_user(request)
    
    db = get_db()
    cursor = db.cursor()
    try:
        cursor.execute("""
            SELECT o.id, o.order_number, o.order_type, o.currency, o.total, o.created_at, o.payment_status,
                   b.title as book_title, b.author_name, b.cover_image_url
            FROM orders o
            JOIN order_items oi ON oi.order_id = o.id
            JOIN books b ON b.id = oi.book_id
            WHERE o.user_id = %s
            ORDER BY o.created_at DESC
        """, (user["id"],))
        
        purchases = cursor.fetchall()
        
        return [dict(row) for row in purchases]
        
    finally:
        db.close()
