"""Base de datos simulada (en memoria) para las pruebas de integración.

Replica el subconjunto de comportamiento de PostgreSQL/RealDictCursor que
usan los endpoints bajo prueba (SELECT/RETURNING/fetchone/fetchall, commit,
rollback, close). Las pruebas NO tocan ninguna base de datos real.
"""

import copy


def _make_user(user_id, name, email, role):
    return {
        "id": user_id,
        "name": name,
        "email": email,
        "role": role,
        "rayos_balance": 100,
        "is_banned": False,
        "username": name.lower().replace(" ", ""),
    }


class FakeCursor:
    def __init__(self, state):
        self.state = state
        self._last_result = None
        self.rowcount = 0

    def execute(self, query, params=None):
        params = tuple(params or ())
        self.state["log"].append((query, params))
        self.rowcount = 0
        self._last_result = None
        q = " ".join(query.strip().lower().split())

        if q.startswith("select id, name, email, role, rayos_balance, is_banned, username from users"):
            self._last_result = self.state["users"].get(int(params[0]))

        elif q.startswith("select * from books where id"):
            book = self.state["books"].get(params[0])
            self._last_result = dict(book) if book else None

        elif q.startswith("select id, title, content, pdf_path, page_count from books"):
            book = self.state["books"].get(int(params[0]))
            self._last_result = dict(book) if book else None

        elif q.startswith("select id, title, published, page_count, uploader_id from books"):
            book = self.state["books"].get(params[0])
            self._last_result = dict(book) if book else None

        elif q.startswith("select id, published, page_count, uploader_id from books"):
            book = self.state["books"].get(params[0])
            self._last_result = dict(book) if book else None

        elif q.startswith("select id, title, published, uploader_id from books"):
            book = self.state["books"].get(params[0])
            self._last_result = dict(book) if book else None

        elif q.startswith("select uploader_id, title from books"):
            book = self.state["books"].get(params[0])
            if book:
                self._last_result = {"uploader_id": book["uploader_id"], "title": book["title"]}

        elif q.startswith("update books set published = 1") and "returning uploader_id, title" in q:
            book = self.state["books"].get(params[0])
            if book:
                book["published"] = 1
                self._last_result = {"uploader_id": book["uploader_id"], "title": book["title"]}
                self.rowcount = 1

        elif q.startswith("delete from books where id"):
            book = self.state["books"].pop(params[0], None)
            if book:
                self.rowcount = 1

        elif q.startswith("delete from book_pages where book_id"):
            antes = len(self.state["book_pages"])
            self.state["book_pages"] = [
                p for p in self.state["book_pages"] if p[0] != int(params[0])
            ]
            self.rowcount = antes - len(self.state["book_pages"])

        elif q.startswith("delete from chapters where book_id"):
            antes = len(self.state["chapters"])
            self.state["chapters"] = [
                c for c in self.state["chapters"] if c[0] != int(params[0])
            ]
            self.rowcount = antes - len(self.state["chapters"])

        elif q.startswith("insert into books") and "returning id" in q:
            new_id = self.state["next_book_id"]
            self.state["next_book_id"] += 1
            title, author_name, content, category, price, cover_url, pdf_path, published, now, uploader_id = params
            self.state["books"][new_id] = {
                "id": new_id,
                "title": title,
                "author_name": author_name,
                "content": content,
                "category": category,
                "price": price,
                "cover_image_url": cover_url,
                "pdf_path": pdf_path,
                "views": 0,
                "likes": 0,
                "dislikes": 0,
                "average_rating": 0.0,
                "total_reviews": 0,
                "published": published,
                "created_at": now,
                "uploader_id": uploader_id,
                "page_count": 0,
            }
            self._last_result = {"id": new_id}
            self.rowcount = 1

        elif q.startswith("insert into notifications"):
            self.state["notifications"].append(params)
            self.rowcount = 1

        elif q.startswith("insert into chapters") and "returning id" in q:
            self.state["chapters"].append(params)
            self._last_result = {"id": len(self.state["chapters"])}
            self.rowcount = 1

        elif q.startswith("insert into book_pages"):
            self.state["book_pages"].append(params)
            self.rowcount = 1

        elif q.startswith("update books set page_count") and "paginated_at" in q:
            book = self.state["books"].get(int(params[2]))
            if book:
                book["page_count"] = params[0]
                book["paginated_at"] = params[1]

        elif q.startswith("update books set page_count"):
            book = self.state["books"].get(params[1])
            if book:
                book["page_count"] = params[0]

        elif q.startswith("update books set views"):
            book = self.state["books"].get(params[0])
            if book:
                book["views"] = book.get("views", 0) + 1

        elif q.startswith("select page_number from reading_progress") or q.startswith("select page_number, reached_at from reading_progress"):
            self._last_result = None

        elif q.startswith("select id from rayos_transactions"):
            self._last_result = None

        elif q.startswith("select count(*) as total from reading_daily_pages"):
            self._last_result = {"total": 0}

        elif q.startswith("select rdp.book_id, b.title, count(*) as pages from reading_daily_pages"):
            self._last_result = []

        elif q.startswith("select p.page_number, p.content, c.id as page_chapter_id, c.title as chapter_title from book_pages"):
            # FASE 8.6: query de contexto de IA por página (con el capítulo al
            # que pertenece la página, para validar page_number+chapter_id).
            book_id, page_number = int(params[0]), int(params[1])
            page = next(
                (p for p in self.state["book_pages"] if p[0] == book_id and p[1] == page_number),
                None,
            )
            if page:
                capitulo_id = None
                capitulo_titulo = None
                if book_id == 10 and page_number == 1 and any(
                    c[0] == 10 for c in self.state["chapters"]
                ):
                    capitulo_id = 1
                    capitulo_titulo = "Capítulo Uno"
                self._last_result = {
                    "page_number": page[1],
                    "content": page[2],
                    "page_chapter_id": capitulo_id,
                    "chapter_title": capitulo_titulo,
                }

        elif q.startswith("select p.page_number, p.content, c.title as chapter_title from book_pages"):
            book_id, page_number = params[0], params[1]
            page = next(
                (p for p in self.state["book_pages"] if p[0] == book_id and p[1] == page_number),
                None,
            )
            if page:
                self._last_result = {"page_number": page[1], "content": page[2], "chapter_title": None}

        elif q.startswith("select id, title, start_page from chapters"):
            self._last_result = []

        # ── FASE 8.3: contexto de IA (capítulo por id) ─────────────────────
        elif q.startswith("select title, start_page from chapters where id"):
            chapter_id, book_id = int(params[0]), int(params[1])
            # En el stub, el único capítulo sembrado (libro 10) usa id = 1.
            self._last_result = (
                {"title": "Capítulo Uno", "start_page": 1}
                if chapter_id == 1 and book_id == 10
                and any(c[0] == 10 for c in self.state["chapters"])
                else None
            )

        # FASE 8.6: siguiente capítulo (límite superior del rango de un capítulo)
        elif q.startswith("select start_page from chapters where book_id") and "order by start_page limit 1" in q:
            book_id, start = int(params[0]), int(params[1])
            siguientes = sorted(
                c[2] for c in self.state["chapters"]
                if c[0] == book_id and c[2] > start
            )
            self._last_result = (
                {"start_page": siguientes[0]} if siguientes else None
            )

        # FASE 8.6: páginas de un rango (capítulo completo, con límite de contexto)
        elif q.startswith("select p.page_number, p.content from book_pages") and "order by p.page_number" in q:
            book_id, desde, hasta = int(params[0]), int(params[1]), int(params[2])
            paginas = [
                {"page_number": p[1], "content": p[2]}
                for p in self.state["book_pages"]
                if p[0] == book_id and desde <= p[1] < hasta
            ]
            self._last_result = sorted(paginas, key=lambda r: r["page_number"])

        elif q.startswith("insert into reading_sessions") or q.startswith("insert into reading_progress"):
            pass

        elif q.startswith("insert into reading_daily_pages"):
            self.rowcount = 0

        # ── FASE 8.5: pre-chequeo de saldo IA (sin reserva) ──────────────────
        elif q.startswith("select rayos_balance from users where id"):
            user = self.state["users"].get(int(params[0]))
            self._last_result = (
                {"rayos_balance": user["rayos_balance"]} if user else None
            )

        # ── FASE 8.5: consumo de IA (idempotencia y registro económico) ─────
        elif q.startswith("select id, user_id, status from ai_consumption where operation_id"):
            row = next(
                (r for r in self.state["ai_consumption"]
                 if r["operation_id"] == params[0]),
                None,
            )
            self._last_result = row

        elif q.startswith("insert into ai_consumption"):
            (user_id, operation_id, operation, provider, model,
             rayos_cost, status, duration_ms, created_at) = params
            if any(
                r["operation_id"] == operation_id
                for r in self.state["ai_consumption"]
            ):
                exc = RuntimeError(
                    "duplicate key value violates unique constraint "
                    "ai_consumption_operation_id_key"
                )
                exc.pgcode = "23505"
                raise exc
            self.state["ai_consumption"].append({
                "id": len(self.state["ai_consumption"]) + 1,
                "user_id": user_id,
                "operation_id": operation_id,
                "operation": operation,
                "provider": provider,
                "model": model,
                "rayos_cost": rayos_cost,
                "status": status,
                "duration_ms": duration_ms,
                "created_at": created_at,
            })
            self._last_result = {"id": len(self.state["ai_consumption"])}
            self.rowcount = 1

        elif q.startswith("update users set rayos_balance = rayos_balance -") and "returning rayos_balance" in q:
            # FASE 8.5: débito atómico condicional (_debit_rayos_atomic).
            # params = (amount, user_id, amount): solo debita si
            # rayos_balance >= amount (nunca saldo negativo).
            amount, user_id, minimum = int(params[0]), int(params[1]), int(params[2])
            user = self.state["users"].get(user_id)
            if user and user.get("rayos_balance", 0) >= minimum:
                user["rayos_balance"] = user.get("rayos_balance", 0) - amount
                self._last_result = {"rayos_balance": user["rayos_balance"]}
                self.rowcount = 1

        elif q.startswith("update users set rayos_balance") and "returning rayos_balance" in q:
            user = self.state["users"].get(int(params[2]))
            if user:
                user["rayos_balance"] = user.get("rayos_balance", 0) + params[0]
                self._last_result = {"rayos_balance": user["rayos_balance"]}
                self.rowcount = 1

        elif q.startswith("select id from users where id") and "for update" in q:
            self._last_result = {"id": int(params[0])}

        elif q.startswith("insert into rayos_transactions"):
            self.state["rayos_transactions"].append(params)
            self.rowcount = 1

        # ── FASE 8.7: persistencia de conversaciones de IA ──────────────────
        elif q.startswith("insert into ai_conversations") and "returning id" in q:
            user_id, title, status, created_at, updated_at = params
            new_id = self.state["next_conversation_id"]
            self.state["next_conversation_id"] += 1
            self.state["ai_conversations"].append({
                "id": new_id,
                "user_id": user_id,
                "title": title,
                "status": status,
                "created_at": created_at,
                "updated_at": updated_at,
            })
            self._last_result = {"id": new_id}
            self.rowcount = 1

        elif q.startswith("select id, title, status, created_at, updated_at from ai_conversations where id"):
            # Ownership estricto: solo la conversación del usuario (404 si
            # no existe O pertenece a otro).
            conv_id, user_id = int(params[0]), int(params[1])
            self._last_result = next(
                (c for c in self.state["ai_conversations"]
                 if c["id"] == conv_id and c["user_id"] == user_id),
                None,
            )

        elif q.startswith("select id, title, status, created_at, updated_at from ai_conversations where user_id") and "order by updated_at desc" in q:
            user_id = int(params[0])
            rows = [
                c for c in self.state["ai_conversations"]
                if c["user_id"] == user_id
            ]
            self._last_result = sorted(
                [
                    {"id": c["id"], "title": c["title"], "status": c["status"],
                     "created_at": c["created_at"], "updated_at": c["updated_at"]}
                    for c in rows
                ],
                key=lambda c: c["updated_at"], reverse=True,
            )

        elif q.startswith("select role, content, created_at from ai_messages") and "order by id" in q:
            conv_id = int(params[0])
            self._last_result = [
                {"role": m["role"], "content": m["content"],
                 "created_at": m["created_at"]}
                for m in self.state["ai_messages"]
                if m["conversation_id"] == conv_id
            ]

        elif q.startswith("insert into ai_messages"):
            conversation_id, role, content, created_at = params
            self.state["ai_messages"].append({
                "id": self.state["next_message_id"],
                "conversation_id": conversation_id,
                "role": role,
                "content": content,
                "created_at": created_at,
            })
            self.state["next_message_id"] += 1
            self.rowcount = 1

        elif q.startswith("update ai_conversations set updated_at"):
            now, conv_id = params[0], int(params[1])
            conv = next(
                (c for c in self.state["ai_conversations"]
                 if c["id"] == conv_id),
                None,
            )
            if conv:
                conv["updated_at"] = now

        elif q.startswith("delete from ai_conversations where id") and "and user_id" in q:
            # FASE 8.7: eliminación con ownership estricto. El CASCADE de
            # mensajes (FK de la BD real) se replica borrando los mensajes.
            conv_id, user_id = int(params[0]), int(params[1])
            conv = next(
                (c for c in self.state["ai_conversations"]
                 if c["id"] == conv_id and c["user_id"] == user_id),
                None,
            )
            if conv:
                self.state["ai_conversations"].remove(conv)
                self.state["ai_messages"] = [
                    m for m in self.state["ai_messages"]
                    if m["conversation_id"] != conv_id
                ]
                self.rowcount = 1

        elif q.startswith("select interaction_type from book_interactions"):
            self._last_result = None

        # ── FASE 4: flujo de registro con QR de referencia ──────────────────
        elif q.startswith("select count(*) as cnt from users where registration_ip"):
            ip, cutoff = params
            self._last_result = {
                "cnt": sum(
                    1
                    for u in self.state["users"].values()
                    if u.get("registration_ip") == ip and u.get("created_at", "") >= cutoff
                )
            }

        elif q.startswith("select id from users where email"):
            self._last_result = next(
                ({"id": uid} for uid, u in self.state["users"].items() if u.get("email") == params[0]),
                None,
            )

        elif q.startswith("select id from qr_codes where code"):
            if "and is_active = true" in q:
                self._last_result = next(
                    (
                        {"id": qr["id"]}
                        for qr in self.state["qr_codes"].values()
                        if qr["code"] == params[0] and qr["is_active"]
                    ),
                    None,
                )
            else:
                self._last_result = next(
                    (
                        {"id": qr["id"]}
                        for qr in self.state["qr_codes"].values()
                        if qr["code"] == params[0]
                    ),
                    None,
                )

        # ── FASE 6: panel administrativo de QR ─────────────────────────────
        elif q.startswith("select q.id, q.code, q.name"):
            rows = []
            for qr_id in sorted(self.state["qr_codes"]):
                qr = self.state["qr_codes"][qr_id]
                rows.append({
                    "id": qr["id"],
                    "code": qr["code"],
                    "name": qr.get("name", ""),
                    "is_active": qr["is_active"],
                    "created_at": qr.get("created_at", ""),
                    "visits_count": sum(
                        1 for v in self.state["qr_visits"] if v[0] == qr_id
                    ),
                    "registrations_count": sum(
                        1
                        for u in self.state["users"].values()
                        if u.get("referred_by_qr_id") == qr_id
                    ),
                })
            self._last_result = rows

        elif q.startswith("select id from qr_codes where id"):
            self._last_result = (
                {"id": int(params[0])} if int(params[0]) in self.state["qr_codes"] else None
            )

        elif q.startswith("insert into qr_codes") and "returning id" in q:
            code, name, created_at = params
            new_id = max(self.state["qr_codes"].keys(), default=0) + 1
            self.state["qr_codes"][new_id] = {
                "id": new_id,
                "code": code,
                "name": name,
                "is_active": True,
                "created_at": created_at,
            }
            self._last_result = {"id": new_id}
            self.rowcount = 1

        elif q.startswith("update qr_codes set is_active"):
            qr = self.state["qr_codes"].get(int(params[1]))
            if qr:
                qr["is_active"] = params[0]
                self.rowcount = 1

        elif q.startswith("insert into users") and "returning id" in q:
            new_id = max(self.state["users"].keys(), default=0) + 1
            name, email, hashed_password, created_at, username, registration_ip, referred_by_qr_id = params
            self.state["users"][new_id] = {
                "id": new_id,
                "name": name,
                "email": email,
                "role": "user",
                "rayos_balance": 0,
                "historical_rayos": 0,
                "username": username,
                "registration_ip": registration_ip,
                "referred_by_qr_id": referred_by_qr_id,
                "is_banned": False,
                "created_at": created_at,
            }
            self._last_result = {"id": new_id}
            self.rowcount = 1

        # ── FASE 5: visitas de QR ────────────────────────────────────────────
        elif q.startswith("insert into qr_visits") and "on conflict" in q:
            qr_id, ip, visit_date, created_at = params
            duplicada = any(
                v[0] == qr_id and v[1] == ip and v[2] == visit_date
                for v in self.state["qr_visits"]
            )
            if not duplicada:
                self.state["qr_visits"].append((qr_id, ip, visit_date, created_at))
                self.rowcount = 1
            else:
                self.rowcount = 0

        elif q.startswith("select count(*)") and "from qr_visits where qr_id" in q:
            self._last_result = {
                "cnt": sum(1 for v in self.state["qr_visits"] if v[0] == params[0])
            }

        elif q.startswith("select count(*)") and "from users where referred_by_qr_id" in q:
            self._last_result = {
                "cnt": sum(
                    1
                    for u in self.state["users"].values()
                    if u.get("referred_by_qr_id") == params[0]
                )
            }

        else:
            raise RuntimeError(
                f"FakeCursor no implementado para la query: {query!r} con params {params!r}"
            )

    def executemany(self, query, seq_of_params):
        for params in seq_of_params:
            self.execute(query, params)

    def fetchone(self):
        result = self._last_result
        self._last_result = None
        return result

    def fetchall(self):
        result = self._last_result
        self._last_result = None
        return result if isinstance(result, list) else []


class FakeDb:
    def __init__(self):
        self.state = {
            "users": {},
            "books": {},
            "notifications": [],
            "chapters": [],
            "book_pages": [],
            "next_book_id": 1,
            "rayos_transactions": [],
            "qr_visits": [],
            "ai_consumption": [],
            "ai_conversations": [],
            "ai_messages": [],
            "next_conversation_id": 1,
            "next_message_id": 1,
            "log": [],
        }
        for uid, name, email, role in [
            (1, "Admin", "admin@test.com", "admin"),
            (2, "Uploader", "uploader@test.com", "user"),
            (3, "Tercero", "tercero@test.com", "user"),
            (4, "Autora", "autora@test.com", "autor"),
        ]:
            self.state["users"][uid] = _make_user(uid, name, email, role)

        # QR de referencia (FASE 4): QR001 activo, QR002 inactivo.
        # QR003 activo adicional (FASE 5) para tests de visita por QR distinto.
        self.state["qr_codes"] = {
            1: {"id": 1, "code": "QR001", "is_active": True},
            2: {"id": 2, "code": "QR002", "is_active": False},
            3: {"id": 3, "code": "QR003", "is_active": True},
        }

        self.state["books"][10] = {
            "id": 10,
            "title": "Libro publicado",
            "author_name": "Autor",
            "content": "contenido publicado",
            "category": "Ficción",
            "price": 0.0,
            "cover_image_url": "http://cover",
            "pdf_path": None,
            "views": 0,
            "likes": 0,
            "dislikes": 0,
            "average_rating": 0.0,
            "total_reviews": 0,
            "published": 1,
            "created_at": "2026-01-01T00:00:00+00:00",
            "uploader_id": 2,
            "page_count": 1,
        }
        self.state["book_pages"].append((10, 1, "página del libro publicado"))

        self.state["books"][20] = {
            "id": 20,
            "title": "Libro pendiente",
            "author_name": "Uploader",
            "content": "contenido pendiente",
            "category": "Ficción",
            "price": 0.0,
            "cover_image_url": "http://cover",
            "pdf_path": None,
            "views": 0,
            "likes": 0,
            "dislikes": 0,
            "average_rating": 0.0,
            "total_reviews": 0,
            "published": 0,
            "created_at": "2026-01-02T00:00:00+00:00",
            "uploader_id": 2,
            "page_count": 1,
        }
        self.state["book_pages"].append((20, 1, "página del libro pendiente"))

        self.state["books"][30] = {
            "id": 30,
            "title": "Pendiente sin uploader",
            "author_name": "Desconocido",
            "content": "Contenido de texto no disponible.",
            "category": "Clásicos",
            "price": 0.0,
            "cover_image_url": "http://cover",
            "pdf_path": None,
            "views": 0,
            "likes": 0,
            "dislikes": 0,
            "average_rating": 0.0,
            "total_reviews": 0,
            "published": 0,
            "created_at": "2026-01-03T00:00:00+00:00",
            "uploader_id": None,
            "page_count": 1,
        }

        self.state["books"][40] = {
            "id": 40,
            "title": "Publicado sin uploader",
            "author_name": "Desconocido",
            "content": "Contenido de texto no disponible.",
            "category": "Clásicos",
            "price": 0.0,
            "cover_image_url": "http://cover",
            "pdf_path": None,
            "views": 0,
            "likes": 0,
            "dislikes": 0,
            "average_rating": 0.0,
            "total_reviews": 0,
            "published": 1,
            "created_at": "2026-01-04T00:00:00+00:00",
            "uploader_id": None,
            "page_count": 1,
        }
        self.state["book_pages"].append((40, 1, "página del publicado sin uploader"))

        self.state["books"][50] = {
            "id": 50,
            "title": "Libro limpio con capítulos",
            "author_name": "Autor",
            "content": _contenido_con_capitulos(),
            "category": "Ficción",
            "price": 0.0,
            "cover_image_url": "http://cover",
            "pdf_path": None,
            "views": 0,
            "likes": 0,
            "dislikes": 0,
            "average_rating": 0.0,
            "total_reviews": 0,
            "published": 1,
            "created_at": "2026-01-05T00:00:00+00:00",
            "uploader_id": 2,
            "page_count": 0,
            "paginated_at": None,
        }

        self.state["books"][51] = {
            "id": 51,
            "title": "Libro patológico",
            "author_name": "Autor",
            "content": _contenido_patologico(),
            "category": "Ficción",
            "price": 0.0,
            "cover_image_url": "http://cover",
            "pdf_path": None,
            "views": 0,
            "likes": 0,
            "dislikes": 0,
            "average_rating": 0.0,
            "total_reviews": 0,
            "published": 1,
            "created_at": "2026-01-06T00:00:00+00:00",
            "uploader_id": 2,
            "page_count": 2,
            "paginated_at": None,
        }
        self.state["book_pages"].append((51, 1, "página vieja 1"))
        self.state["book_pages"].append((51, 2, "página vieja 2"))

        self.state["books"][52] = {
            "id": 52,
            "title": "Libro limpio reemplazable",
            "author_name": "Autor",
            "content": _contenido_variado(1400),
            "category": "Ficción",
            "price": 0.0,
            "cover_image_url": "http://cover",
            "pdf_path": None,
            "views": 0,
            "likes": 0,
            "dislikes": 0,
            "average_rating": 0.0,
            "total_reviews": 0,
            "published": 1,
            "created_at": "2026-01-07T00:00:00+00:00",
            "uploader_id": 2,
            "page_count": 1,
            "paginated_at": None,
        }
        self.state["book_pages"].append((52, 1, "página vieja"))

        self.state["books"][53] = {
            "id": 53,
            "title": "Libro con PDF",
            "author_name": "Autor",
            "content": "contenido viejo",
            "category": "Ficción",
            "price": 0.0,
            "cover_image_url": "http://cover",
            "pdf_path": None,
            "views": 0,
            "likes": 0,
            "dislikes": 0,
            "average_rating": 0.0,
            "total_reviews": 0,
            "published": 1,
            "created_at": "2026-01-08T00:00:00+00:00",
            "uploader_id": 2,
            "page_count": 1,
            "paginated_at": None,
        }
        self.state["book_pages"].append((53, 1, "página vieja pdf"))

        self.state["books"][54] = {
            "id": 54,
            "title": "Libro PDF corrupto",
            "author_name": "Autor",
            "content": "contenido viejo",
            "category": "Ficción",
            "price": 0.0,
            "cover_image_url": "http://cover",
            "pdf_path": None,
            "views": 0,
            "likes": 0,
            "dislikes": 0,
            "average_rating": 0.0,
            "total_reviews": 0,
            "published": 1,
            "created_at": "2026-01-09T00:00:00+00:00",
            "uploader_id": 2,
            "page_count": 1,
            "paginated_at": None,
        }
        self.state["book_pages"].append((54, 1, "página vieja corrupto"))

        self._commit_point = copy.deepcopy(self.state)

    def cursor(self):
        return FakeCursor(self.state)

    def commit(self):
        self._commit_point = copy.deepcopy(self.state)

    def rollback(self):
        estado = copy.deepcopy(self._commit_point)
        estado["log"] = self.state["log"]
        self.state = estado

    def close(self):
        pass


def _contenido_con_capitulos():
    """Dos capítulos reconocibles + párrafos largos variados (5 páginas)."""
    para_uno = " ".join(
        f"El viajero {i} cruzó el valle al amanecer mientras la niebla {i} "
        f"cubría los campos {i} y el río {i} brillaba bajo el sol de la mañana."
        for i in range(16)
    )
    para_dos = " ".join(
        f"En la aldea {i} los campesinos {i} preparaban la cosecha {i} con "
        f"calma y paciencia {i} bajo el cielo despejado de la tarde."
        for i in range(16)
    )
    return f"CAPÍTULO 1\n\n{para_uno}\n\nCAPÍTULO 2: El segundo\n\n{para_dos}"


def _contenido_patologico():
    """Párrafo idéntico repetido 8 veces: dispara el detector de fragmentos."""
    parrafo = (
        "Este es un párrafo de ejemplo que se repite de forma idéntica muchas "
        "veces para simular contenido corrupto y duplicado en un libro de la "
        "plataforma de lectura con páginas infinitas. "
    )
    return "\n\n".join([parrafo] * 8)


def _contenido_variado(longitud):
    """Texto largo variado sin encabezados ni frases repetidas (limpio)."""
    parrafos = []
    total = 0
    i = 0
    while total < longitud:
        parrafo = (
            f"Párrafo {i}: aquí {i} transcurre la acción {i} del capítulo con "
            f"detalles {i} únicos sobre el lugar {i} y los personajes {i} del "
            f"relato. El clima {i} cambió hacia el final {i} de la escena {i} "
            f"y los acontecimientos {i} marcaron un giro {i} en la historia {i} "
            f"contada con ritmo pausado en la página {i}."
        )
        parrafos.append(parrafo)
        total += len(parrafo)
        i += 1
    return "\n\n".join(parrafos)