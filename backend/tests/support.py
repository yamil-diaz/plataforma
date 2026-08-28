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

        elif q.startswith("select count(*) as cnt from book_pages where book_id"):
            book_id = int(params[0])
            cnt = sum(1 for p in self.state["book_pages"] if p[0] == book_id)
            self._last_result = {"cnt": cnt}

        elif q.startswith("select id, title, published, uploader_id from books"):
            book = self.state["books"].get(params[0])
            self._last_result = dict(book) if book else None

        elif q.startswith("select id, title, author_name, content, pdf_path from books where title is not null and author_name is not null"):
            # Duplicate check query
            results = []
            for book in self.state["books"].values():
                if book.get("title") and book.get("author_name"):
                    results.append({
                        "id": book["id"],
                        "title": book["title"],
                        "author_name": book["author_name"],
                        "content": book.get("content", ""),
                        "pdf_path": book.get("pdf_path", "")
                    })
            self._last_result = results

        elif q.startswith("select id, pdf_path from books where pdf_path is not null"):
            # Duplicate check by PDF hash
            results = []
            for book in self.state["books"].values():
                if book.get("pdf_path"):
                    results.append({
                        "id": book["id"],
                        "pdf_path": book.get("pdf_path", "")
                    })
            self._last_result = results

        elif q.startswith("select id from books where content = %s limit 1"):
            # Duplicate check by content hash
            target_content = params[0] if params else ""
            for book in self.state["books"].values():
                if book.get("content") == target_content:
                    self._last_result = {"id": book["id"]}
                    break
            else:
                self._last_result = None

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
            if len(params) == 10:
                title, author_name, content, category, price, cover_url, pdf_path, published, now, uploader_id = params
            else:
                title, author_name, content, category, price, cover_url, pdf_path, now = params
                published = 1
                uploader_id = None
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

        elif q.startswith("select title, start_page from chapters where id"):
            chapter_id, book_id = int(params[0]), int(params[1])
            self._last_result = (
                {"title": "Capítulo Uno", "start_page": 1}
                if chapter_id == 1 and book_id == 10
                and any(c[0] == 10 for c in self.state["chapters"])
                else None
            )

        elif q.startswith("select start_page from chapters where book_id") and "order by start_page limit 1" in q:
            book_id, start = int(params[0]), int(params[1])
            siguientes = sorted(
                c[2] for c in self.state["chapters"]
                if c[0] == book_id and c[2] > start
            )
            self._last_result = (
                {"start_page": siguientes[0]} if siguientes else None
            )

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

        elif q.startswith("select rayos_balance from users where id"):
            user = self.state["users"].get(int(params[0]))
            self._last_result = (
                {"rayos_balance": user["rayos_balance"]} if user else None
            )

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

        elif q.startswith("select b.id, b.title, b.author_name, b.category, b.price, b.cover_image_url, b.views, b.likes, b.average_rating, b.total_reviews, fb.display_order from featured_books fb"):
            month, year = int(params[0]), int(params[1])
            results = []
            for fb in sorted(
                [f for f in self.state["featured_books"] if f["month"] == month and f["year"] == year],
                key=lambda f: f["display_order"],
            ):
                book = self.state["books"].get(fb["book_id"])
                if book and book.get("published") == 1:
                    results.append({
                        "id": book["id"],
                        "title": book["title"],
                        "author_name": book["author_name"],
                        "category": book["category"],
                        "price": book["price"],
                        "cover_image_url": book.get("cover_image_url"),
                        "views": book.get("views", 0),
                        "likes": book.get("likes", 0),
                        "average_rating": book.get("average_rating", 0.0),
                        "total_reviews": book.get("total_reviews", 0),
                        "display_order": fb["display_order"],
                    })
            self._last_result = results[:20]

        elif q.startswith("select fb.id, fb.book_id, fb.display_order, fb.month, fb.year, fb.added_by, fb.created_at"):
            month, year = int(params[0]), int(params[1])
            results = []
            for fb in sorted(
                [f for f in self.state["featured_books"] if f["month"] == month and f["year"] == year],
                key=lambda f: f["display_order"],
            ):
                book = self.state["books"].get(fb["book_id"])
                results.append({
                    "id": fb["id"],
                    "book_id": fb["book_id"],
                    "display_order": fb["display_order"],
                    "month": fb["month"],
                    "year": fb["year"],
                    "added_by": fb["added_by"],
                    "created_at": fb["created_at"],
                    "title": book["title"] if book else "",
                    "author_name": book["author_name"] if book else "",
                    "category": book["category"] if book else "",
                    "price": book["price"] if book else 0,
                    "cover_image_url": book.get("cover_image_url") if book else None,
                    "published": book.get("published", 0) if book else 0,
                })
            self._last_result = results

        elif q.startswith("select id, published from books where id = any"):
            ids_param = params[0]
            results = []
            for bid in ids_param:
                book = self.state["books"].get(bid)
                if book:
                    results.append({"id": book["id"], "published": book.get("published", 0)})
            self._last_result = results

        elif q.startswith("delete from featured_books where month = %s and year = %s"):
            month, year = int(params[0]), int(params[1])
            antes = len(self.state["featured_books"])
            self.state["featured_books"] = [
                f for f in self.state["featured_books"]
                if not (f["month"] == month and f["year"] == year)
            ]
            self.rowcount = antes - len(self.state["featured_books"])

        elif q.startswith("insert into featured_books") and "returning id" not in q:
            book_id, display_order, month, year, added_by, created_at = params
            new_id = self.state["next_featured_id"]
            self.state["next_featured_id"] += 1
            self.state["featured_books"].append({
                "id": new_id,
                "book_id": book_id,
                "display_order": display_order,
                "month": month,
                "year": year,
                "added_by": added_by,
                "created_at": created_at,
            })
            self.rowcount = 1

        elif q.startswith("delete from featured_books where book_id = %s and month = %s and year = %s"):
            book_id, month, year = int(params[0]), int(params[1]), int(params[2])
            antes = len(self.state["featured_books"])
            self.state["featured_books"] = [
                f for f in self.state["featured_books"]
                if not (f["book_id"] == book_id and f["month"] == month and f["year"] == year)
            ]
            self.rowcount = antes - len(self.state["featured_books"])

        # ── Books list (pre-existing) ──────────────────────────────────
        elif q.startswith("select * from books where published = 1"):
            books = [dict(b) for b in self.state["books"].values() if b.get("published") == 1]
            self._last_result = books

        # ── FORO ESTUDIANTIL ────────────────────────────────────────────

        # --- CATEGORIES ---
        elif q.startswith("select id, name, description, icon, color, sort_order, is_active, post_count, created_at from forum_categories") and "where id" not in q:
            cats = self.state["forum_categories"]
            self._last_result = sorted(cats, key=lambda c: c.get("sort_order", 0))
        elif q.startswith("select id, name, description, icon, color, sort_order, is_active, post_count from forum_categories") and "where id" not in q:
            cats = [c for c in self.state["forum_categories"] if c.get("is_active")]
            self._last_result = sorted(cats, key=lambda c: c.get("sort_order", 0))

        elif q.startswith("select id, post_count from forum_categories where id"):
            cat_id = int(params[0])
            cat = next((c for c in self.state["forum_categories"] if c["id"] == cat_id), None)
            self._last_result = {"id": cat["id"], "post_count": cat.get("post_count", 0)} if cat else None

        elif q.startswith("select id, is_active from forum_categories where id"):
            cat_id = int(params[0])
            cat = next((c for c in self.state["forum_categories"] if c["id"] == cat_id), None)
            self._last_result = {"id": cat["id"], "is_active": cat.get("is_active", True)} if cat else None

        elif q.startswith("select id from forum_categories where id"):
            cat_id = int(params[0])
            cat = next((c for c in self.state["forum_categories"] if c["id"] == cat_id), None)
            self._last_result = {"id": cat_id} if cat else None

        elif q.startswith("select count(*) as total from forum_categories"):
            self._last_result = {"total": len([c for c in self.state["forum_categories"] if c.get("is_active", True)])}

        elif q.startswith("insert into forum_categories") and "returning id" in q:
            name, description, icon, color, _, created_at = params
            new_id = max((c["id"] for c in self.state["forum_categories"]), default=0) + 1
            self.state["forum_categories"].append({
                "id": new_id, "name": name, "description": description,
                "icon": icon, "color": color, "sort_order": 0,
                "is_active": True, "post_count": 0, "created_at": created_at,
            })
            self._last_result = {"id": new_id}
            self.rowcount = 1

        elif q.startswith("update forum_categories set") and "where id = %s" in q:
            cat_id = int(params[-1])
            for c in self.state["forum_categories"]:
                if c["id"] == cat_id:
                    self.rowcount = 1
                    break

        elif q.startswith("delete from forum_categories where id"):
            cat_id = int(params[0])
            antes = len(self.state["forum_categories"])
            self.state["forum_categories"] = [c for c in self.state["forum_categories"] if c["id"] != cat_id]
            self.rowcount = antes - len(self.state["forum_categories"])

        # --- POSTS (list count with fp alias) ---
        elif q.startswith("select count(*) as total from forum_posts fp"):
            active_posts = [p for p in self.state["forum_posts"] if p.get("status") == "active"]
            cat_filter = None
            book_filter = None
            user_filter = None
            parts = q.split("where")[-1]
            param_idx = 0
            for part in parts.split("and"):
                part = part.strip()
                if "category_id = %s" in part:
                    cat_filter = int(params[param_idx])
                    param_idx += 1
                elif "book_id = %s" in part:
                    book_filter = int(params[param_idx])
                    param_idx += 1
                elif "user_id = %s" in part:
                    user_filter = int(params[param_idx])
                    param_idx += 1
                else:
                    param_idx += 1
            filtered = active_posts
            if cat_filter is not None:
                filtered = [p for p in filtered if p.get("category_id") == cat_filter]
            if book_filter is not None:
                filtered = [p for p in filtered if p.get("book_id") == book_filter]
            if user_filter is not None:
                filtered = [p for p in filtered if p.get("user_id") == user_filter]
            self._last_result = {"total": len(filtered)}

        # --- POSTS (list with JOIN) ---
        elif q.startswith("select fp.id, fp.user_id, u.username as author_username, u.name as author_name, fp.category_id, fc.name as category_name, fc.icon as category_icon, fc.color as category_color, fp.title, fp.slug, fp.status, fp.views, fp.reply_count, fp.like_count, fp.is_pinned, fp.is_resolved, fp.book_id, fp.created_at, fp.updated_at from forum_posts fp"):
            status_filter = None
            cat_filter = None
            book_filter = None
            user_filter = None
            params_used = 0
            for clause in ("fp.status = %s", "fp.category_id = %s", "fp.book_id = %s", "fp.user_id = %s"):
                if clause in q:
                    idx = q.index(clause)
                    before = q[:idx].count("%s")
                    if before < len(params):
                        val = params[before]
                        if clause == "fp.status = %s":
                            status_filter = val
                        elif clause == "fp.category_id = %s":
                            cat_filter = int(val)
                        elif clause == "fp.book_id = %s":
                            book_filter = int(val)
                        elif clause == "fp.user_id = %s":
                            user_filter = int(val)
            posts = []
            for p in self.state["forum_posts"]:
                if status_filter and p.get("status") != status_filter:
                    continue
                if cat_filter is not None and p.get("category_id") != cat_filter:
                    continue
                if book_filter is not None and p.get("book_id") != book_filter:
                    continue
                if user_filter is not None and p.get("user_id") != user_filter:
                    continue
                cat = next((c for c in self.state["forum_categories"] if c["id"] == p.get("category_id")), None)
                user = self.state["users"].get(p.get("user_id"))
                posts.append({
                    "id": p["id"], "user_id": p.get("user_id"),
                    "author_username": user["username"] if user else None,
                    "author_name": user["name"] if user else None,
                    "category_id": p.get("category_id"),
                    "category_name": cat["name"] if cat else None,
                    "category_icon": cat.get("icon") if cat else None,
                    "category_color": cat.get("color") if cat else None,
                    "title": p["title"], "slug": p.get("slug", ""),
                    "status": p.get("status", "active"),
                    "views": p.get("views", 0), "reply_count": p.get("reply_count", 0),
                    "like_count": p.get("like_count", 0),
                    "is_pinned": p.get("is_pinned", False),
                    "is_resolved": p.get("is_resolved", False),
                    "book_id": p.get("book_id"),
                    "created_at": p["created_at"], "updated_at": p.get("updated_at", ""),
                })
            posts.sort(key=lambda p: (not p["is_pinned"], p["created_at"]), reverse=True)
            self._last_result = posts

        # --- POSTS (get single with JOINs) ---
        elif q.startswith("select fp.*, u.username as author_username, u.name as author_name, fc.name as category_name, fc.icon as category_icon, fc.color as category_color, b.title as book_title from forum_posts fp"):
            post_id = int(params[0])
            post = next((p for p in self.state["forum_posts"] if p["id"] == post_id), None)
            if post:
                cat = next((c for c in self.state["forum_categories"] if c["id"] == post.get("category_id")), None)
                user = self.state["users"].get(post.get("user_id"))
                book = self.state["books"].get(post.get("book_id")) if post.get("book_id") else None
                self._last_result = {
                    **post,
                    "author_username": user["username"] if user else None,
                    "author_name": user["name"] if user else None,
                    "category_name": cat["name"] if cat else None,
                    "category_icon": cat.get("icon") if cat else None,
                    "category_color": cat.get("color") if cat else None,
                    "book_title": book["title"] if book else None,
                }
            else:
                self._last_result = None

        elif q.startswith("update forum_posts set views = views + 1 where id"):
            post_id = int(params[0])
            for p in self.state["forum_posts"]:
                if p["id"] == post_id:
                    p["views"] = p.get("views", 0) + 1
                    break

        elif q.startswith("select 1 from forum_likes where post_id"):
            post_id, user_id = int(params[0]), int(params[1])
            like = next(
                (l for l in self.state["forum_likes"]
                 if l.get("post_id") == post_id and l.get("user_id") == user_id),
                None,
            )
            self._last_result = like if like else None

        elif q.startswith("select 1 from forum_bookmarks where post_id"):
            post_id, user_id = int(params[0]), int(params[1])
            bm = next(
                (b for b in self.state["forum_bookmarks"]
                 if b.get("post_id") == post_id and b.get("user_id") == user_id),
                None,
            )
            self._last_result = bm if bm else None

        elif q.startswith("select 1 from forum_follows where post_id"):
            post_id, user_id = int(params[0]), int(params[1])
            fol = next(
                (f for f in self.state["forum_follows"]
                 if f.get("post_id") == post_id and f.get("user_id") == user_id),
                None,
            )
            self._last_result = fol if fol else None

        # --- POSTS (create) ---
        elif q.startswith("insert into forum_posts") and "returning id" in q:
            user_id, category_id, title, content, book_id, slug, created_at, updated_at = params
            new_id = max((p["id"] for p in self.state["forum_posts"]), default=0) + 1
            self.state["forum_posts"].append({
                "id": new_id, "user_id": user_id, "category_id": category_id,
                "title": title, "content": content, "book_id": book_id,
                "slug": slug, "like_count": 0, "reply_count": 0, "views": 0,
                "is_pinned": False, "is_resolved": False, "status": "active",
                "created_at": created_at, "updated_at": updated_at,
            })
            self._last_result = {"id": new_id}
            self.rowcount = 1

        elif q.startswith("update forum_categories set post_count = post_count + 1 where id"):
            cat_id = int(params[0])
            for c in self.state["forum_categories"]:
                if c["id"] == cat_id:
                    c["post_count"] = c.get("post_count", 0) + 1
                    break

        # --- POSTS (update - fetch ownership) ---
        elif q.startswith("select id, user_id, status from forum_posts where id"):
            post_id = int(params[0])
            post = next((p for p in self.state["forum_posts"] if p["id"] == post_id), None)
            self._last_result = {"id": post["id"], "user_id": post["user_id"], "status": post.get("status", "active")} if post else None

        # --- POSTS (update - dynamic SET) ---
        elif q.startswith("update forum_posts set") and "where id = %s" in q and "like_count" not in q and "views" not in q and "is_pinned" not in q and "reply_count" not in q and "is_resolved" not in q:
            post_id = int(params[-1])
            for p in self.state["forum_posts"]:
                if p["id"] == post_id:
                    self.rowcount = 1
                    break

        # --- POSTS (delete - fetch with category_id) ---
        elif q.startswith("select id, user_id, status, category_id from forum_posts where id"):
            post_id = int(params[0])
            post = next((p for p in self.state["forum_posts"] if p["id"] == post_id), None)
            self._last_result = {
                "id": post["id"], "user_id": post["user_id"],
                "status": post.get("status", "active"),
                "category_id": post.get("category_id"),
            } if post else None

        elif q.startswith("update forum_posts set status = 'deleted', updated_at = %s where id"):
            _, post_id = params[0], int(params[1])
            for p in self.state["forum_posts"]:
                if p["id"] == post_id:
                    p["status"] = "deleted"
                    self.rowcount = 1
                    break

        elif q.startswith("update forum_categories set post_count = greatest(post_count - 1, 0) where id"):
            cat_id = int(params[0])
            for c in self.state["forum_categories"]:
                if c["id"] == cat_id:
                    c["post_count"] = max(c.get("post_count", 0) - 1, 0)
                    break

        # --- POSTS (admin: status / pin) ---
        elif q.startswith("select id, status, category_id from forum_posts where id"):
            post_id = int(params[0])
            post = next((p for p in self.state["forum_posts"] if p["id"] == post_id), None)
            self._last_result = {"id": post["id"], "status": post.get("status", "active"), "category_id": post.get("category_id")} if post else None

        elif q.startswith("select id, status from forum_posts where id"):
            post_id = int(params[0])
            post = next((p for p in self.state["forum_posts"] if p["id"] == post_id), None)
            self._last_result = {"id": post["id"], "status": post.get("status", "active")} if post else None

        elif q.startswith("select id, is_pinned from forum_posts where id"):
            post_id = int(params[0])
            post = next((p for p in self.state["forum_posts"] if p["id"] == post_id), None)
            self._last_result = {"id": post["id"], "is_pinned": post.get("is_pinned", False)} if post else None

        elif q.startswith("update forum_posts set is_pinned"):
            is_pinned, post_id = params[0], int(params[1])
            for p in self.state["forum_posts"]:
                if p["id"] == post_id:
                    p["is_pinned"] = is_pinned
                    self.rowcount = 1
                    break

        elif q.startswith("update forum_posts set status = %s where id"):
            status, post_id = params[0], int(params[1])
            for p in self.state["forum_posts"]:
                if p["id"] == post_id:
                    p["status"] = status
                    self.rowcount = 1
                    break

        elif q.startswith("update forum_posts set is_resolved"):
            val, post_id = params[0], int(params[1])
            for p in self.state["forum_posts"]:
                if p["id"] == post_id:
                    p["is_resolved"] = val
                    break

        # --- POSTS count (generic) ---
        elif q.startswith("select count(*) as total from forum_posts"):
            if "where user_id = %s and status != 'deleted'" in q:
                uid = int(params[0])
                self._last_result = {
                    "total": len([p for p in self.state["forum_posts"]
                                  if p.get("user_id") == uid and p.get("status") != "deleted"])
                }
            elif "where book_id = %s and status = 'active'" in q:
                bid = int(params[0])
                self._last_result = {
                    "total": len([p for p in self.state["forum_posts"]
                                  if p.get("book_id") == bid and p.get("status") == "active"])
                }
            elif "status != 'deleted'" in q:
                self._last_result = {
                    "total": len([p for p in self.state["forum_posts"]
                                  if p.get("status") != "deleted"])
                }
            elif "where status = %s" in q:
                sf = params[0]
                self._last_result = {
                    "total": len([p for p in self.state["forum_posts"] if p.get("status") == sf])
                }
            else:
                self._last_result = {"total": len(self.state["forum_posts"])}

        # --- BOOK FORUM POSTS ---
        elif q.startswith("select fp.id, fp.title, fp.slug, fp.user_id, u.username as author_username, fp.reply_count, fp.like_count, fp.created_at from forum_posts fp"):
            bid = int(params[0])
            posts = [p for p in self.state["forum_posts"]
                     if p.get("book_id") == bid and p.get("status") == "active"]
            result = []
            for p in posts:
                user = self.state["users"].get(p.get("user_id"))
                result.append({
                    "id": p["id"], "title": p["title"], "slug": p.get("slug", ""),
                    "user_id": p.get("user_id"),
                    "author_username": user["username"] if user else None,
                    "reply_count": p.get("reply_count", 0),
                    "like_count": p.get("like_count", 0),
                    "created_at": p["created_at"],
                })
            self._last_result = sorted(result, key=lambda p: p["created_at"], reverse=True)[:5]

        # --- REPLIES (list) ---
        elif q.startswith("select fr.id, fr.user_id, u.username as author_username, u.name as author_name, fr.content, fr.status, fr.is_accepted, fr.like_count, fr.created_at, fr.updated_at from forum_replies fr"):
            post_id = int(params[0])
            replies = [r for r in self.state["forum_replies"]
                       if r.get("post_id") == post_id and r.get("status") == "active"]
            replies.sort(key=lambda r: (not r.get("is_accepted", False), r.get("created_at", "")))
            limit = int(params[1]) if len(params) > 1 else 20
            offset = int(params[2]) if len(params) > 2 else 0
            replies = replies[offset:offset + limit]
            result = []
            for r in replies:
                user = self.state["users"].get(r.get("user_id"))
                result.append({
                    "id": r["id"], "user_id": r.get("user_id"),
                    "author_username": user["username"] if user else None,
                    "author_name": user["name"] if user else None,
                    "content": r["content"], "status": r.get("status", "active"),
                    "is_accepted": r.get("is_accepted", False),
                    "like_count": r.get("like_count", 0),
                    "created_at": r["created_at"], "updated_at": r.get("updated_at", ""),
                })
            self._last_result = result

        elif q.startswith("select count(*) as total from forum_replies where post_id = %s and status = 'active'"):
            post_id = int(params[0])
            self._last_result = {
                "total": len([r for r in self.state["forum_replies"]
                              if r.get("post_id") == post_id and r.get("status") == "active"])
            }

        # --- REPLIES (create) ---
        elif q.startswith("select id, status, user_id, title from forum_posts where id"):
            post_id = int(params[0])
            post = next((p for p in self.state["forum_posts"] if p["id"] == post_id), None)
            self._last_result = {
                "id": post["id"], "status": post.get("status", "active"),
                "user_id": post.get("user_id"), "title": post.get("title", ""),
            } if post else None

        elif q.startswith("insert into forum_replies") and "returning id" in q:
            post_id, user_id, content, created_at, updated_at = params
            new_id = max((r["id"] for r in self.state["forum_replies"]), default=0) + 1
            self.state["forum_replies"].append({
                "id": new_id, "post_id": post_id, "user_id": user_id,
                "content": content, "status": "active", "is_accepted": False,
                "like_count": 0, "created_at": created_at, "updated_at": updated_at,
            })
            self._last_result = {"id": new_id}
            self.rowcount = 1

        elif q.startswith("update forum_posts set reply_count = reply_count + 1 where id"):
            post_id = int(params[0])
            for p in self.state["forum_posts"]:
                if p["id"] == post_id:
                    p["reply_count"] = p.get("reply_count", 0) + 1
                    break

        elif q.startswith("select user_id from forum_follows where post_id = %s and user_id != %s"):
            post_id, exclude_id = int(params[0]), int(params[1])
            self._last_result = [
                {"user_id": f["user_id"]}
                for f in self.state["forum_follows"]
                if f.get("post_id") == post_id and f.get("user_id") != exclude_id
            ]

        # --- REPLIES (update) ---
        elif q.startswith("select id, user_id, status from forum_replies where id"):
            reply_id = int(params[0])
            reply = next((r for r in self.state["forum_replies"] if r["id"] == reply_id), None)
            self._last_result = {
                "id": reply["id"], "user_id": reply.get("user_id"), "status": reply.get("status", "active"),
            } if reply else None

        elif q.startswith("update forum_replies set content"):
            content, updated_at, reply_id = params
            for r in self.state["forum_replies"]:
                if r["id"] == reply_id:
                    r["content"] = content
                    r["updated_at"] = updated_at
                    self.rowcount = 1
                    break

        # --- REPLIES (delete) ---
        elif q.startswith("select id, user_id, post_id, is_accepted, status from forum_replies where id"):
            reply_id = int(params[0])
            reply = next((r for r in self.state["forum_replies"] if r["id"] == reply_id), None)
            self._last_result = {
                "id": reply["id"], "user_id": reply.get("user_id"),
                "post_id": reply.get("post_id"),
                "is_accepted": reply.get("is_accepted", False),
                "status": reply.get("status", "active"),
            } if reply else None

        elif q.startswith("update forum_replies set status = 'deleted', updated_at = %s where id"):
            _, reply_id = params[0], int(params[1])
            for r in self.state["forum_replies"]:
                if r["id"] == reply_id:
                    r["status"] = "deleted"
                    self.rowcount = 1
                    break

        elif q.startswith("update forum_posts set reply_count = greatest(reply_count - 1, 0) where id"):
            post_id = int(params[0])
            for p in self.state["forum_posts"]:
                if p["id"] == post_id:
                    p["reply_count"] = max(p.get("reply_count", 0) - 1, 0)
                    break

        # --- REPLIES (accept) ---
        elif q.startswith("select fr.id, fr.post_id, fr.user_id, fr.status from forum_replies fr where fr.id"):
            reply_id = int(params[0])
            reply = next((r for r in self.state["forum_replies"] if r["id"] == reply_id), None)
            self._last_result = {
                "id": reply["id"], "post_id": reply.get("post_id"),
                "user_id": reply.get("user_id"), "status": reply.get("status", "active"),
            } if reply else None

        elif q.startswith("update forum_replies set is_accepted = false where post_id = %s and is_accepted = true"):
            post_id = int(params[0])
            for r in self.state["forum_replies"]:
                if r.get("post_id") == post_id and r.get("is_accepted"):
                    r["is_accepted"] = False

        elif q.startswith("update forum_replies set is_accepted = true where id"):
            reply_id = int(params[0])
            for r in self.state["forum_replies"]:
                if r["id"] == reply_id:
                    r["is_accepted"] = True
                    break

        # --- REPLIES (admin set status) ---
        elif q.startswith("select id, status, post_id from forum_replies where id"):
            reply_id = int(params[0])
            reply = next((r for r in self.state["forum_replies"] if r["id"] == reply_id), None)
            self._last_result = {
                "id": reply["id"], "status": reply.get("status", "active"),
                "post_id": reply.get("post_id"),
            } if reply else None

        elif q.startswith("update forum_replies set status = %s, updated_at = %s where id"):
            status, _, reply_id = params[0], params[1], int(params[2])
            for r in self.state["forum_replies"]:
                if r["id"] == reply_id:
                    r["status"] = status
                    self.rowcount = 1
                    break

        # --- LIKES (post likes) ---
        elif q.startswith("select id from forum_likes where post_id"):
            post_id, user_id = int(params[0]), int(params[1])
            like = next(
                (l for l in self.state["forum_likes"]
                 if l.get("post_id") == post_id and l.get("user_id") == user_id),
                None,
            )
            self._last_result = {"id": like["id"]} if like else None

        elif q.startswith("delete from forum_likes where id"):
            like_id = int(params[0])
            antes = len(self.state["forum_likes"])
            self.state["forum_likes"] = [l for l in self.state["forum_likes"] if l["id"] != like_id]
            self.rowcount = antes - len(self.state["forum_likes"])

        elif q.startswith("insert into forum_likes"):
            post_id, user_id, created_at = params
            new_id = max((l["id"] for l in self.state["forum_likes"]), default=0) + 1
            self.state["forum_likes"].append({
                "id": new_id, "post_id": post_id, "user_id": user_id, "created_at": created_at,
            })
            self._last_result = {"id": new_id}
            self.rowcount = 1

        elif q.startswith("update forum_posts set like_count = greatest(like_count - 1, 0) where id"):
            post_id = int(params[0])
            for p in self.state["forum_posts"]:
                if p["id"] == post_id:
                    p["like_count"] = max(p.get("like_count", 0) - 1, 0)
                    break

        elif q.startswith("update forum_posts set like_count = like_count + 1 where id"):
            post_id = int(params[0])
            for p in self.state["forum_posts"]:
                if p["id"] == post_id:
                    p["like_count"] = p.get("like_count", 0) + 1
                    break

        elif q.startswith("select like_count from forum_posts where id"):
            post_id = int(params[0])
            post = next((p for p in self.state["forum_posts"] if p["id"] == post_id), None)
            self._last_result = {"like_count": post.get("like_count", 0)} if post else None

        # --- REPLY LIKES ---
        elif q.startswith("update forum_replies set like_count = greatest(like_count - 1, 0) where id"):
            reply_id = int(params[0])
            for r in self.state["forum_replies"]:
                if r["id"] == reply_id:
                    r["like_count"] = max(r.get("like_count", 0) - 1, 0)
                    break

        elif q.startswith("update forum_replies set like_count = like_count + 1 where id"):
            reply_id = int(params[0])
            for r in self.state["forum_replies"]:
                if r["id"] == reply_id:
                    r["like_count"] = r.get("like_count", 0) + 1
                    break

        # --- BOOKMARKS ---
        elif q.startswith("select id, status from forum_posts where id"):
            post_id = int(params[0])
            post = next((p for p in self.state["forum_posts"] if p["id"] == post_id), None)
            self._last_result = {"id": post["id"], "status": post.get("status", "active")} if post else None

        elif q.startswith("select id from forum_bookmarks where post_id"):
            post_id, user_id = int(params[0]), int(params[1])
            bm = next(
                (b for b in self.state["forum_bookmarks"]
                 if b.get("post_id") == post_id and b.get("user_id") == user_id),
                None,
            )
            self._last_result = {"id": bm["id"]} if bm else None

        elif q.startswith("delete from forum_bookmarks where id"):
            bm_id = int(params[0])
            antes = len(self.state["forum_bookmarks"])
            self.state["forum_bookmarks"] = [b for b in self.state["forum_bookmarks"] if b["id"] != bm_id]
            self.rowcount = antes - len(self.state["forum_bookmarks"])

        elif q.startswith("insert into forum_bookmarks"):
            post_id, user_id, created_at = params
            new_id = max((b["id"] for b in self.state["forum_bookmarks"]), default=0) + 1
            self.state["forum_bookmarks"].append({
                "id": new_id, "post_id": post_id, "user_id": user_id, "created_at": created_at,
            })
            self._last_result = {"id": new_id}
            self.rowcount = 1

        # --- BOOKMARKS LIST ---
        elif q.startswith("select fp.id, fp.title, fp.slug, fp.created_at, fp.reply_count, fp.like_count, fc.name as category_name, fc.icon as category_icon from forum_bookmarks fb"):
            user_id = int(params[0])
            bms = [b for b in self.state["forum_bookmarks"] if b.get("user_id") == user_id]
            result = []
            for b in bms:
                post = next((p for p in self.state["forum_posts"] if p["id"] == b.get("post_id") and p.get("status") == "active"), None)
                if not post:
                    continue
                cat = next((c for c in self.state["forum_categories"] if c["id"] == post.get("category_id")), None)
                result.append({
                    "id": post["id"], "title": post["title"], "slug": post.get("slug", ""),
                    "created_at": post["created_at"],
                    "reply_count": post.get("reply_count", 0),
                    "like_count": post.get("like_count", 0),
                    "category_name": cat["name"] if cat else None,
                    "category_icon": cat.get("icon") if cat else None,
                })
            result.sort(key=lambda r: r["created_at"], reverse=True)
            self._last_result = result

        # --- FOLLOWS ---
        elif q.startswith("select id from forum_follows where post_id"):
            post_id, user_id = int(params[0]), int(params[1])
            fol = next(
                (f for f in self.state["forum_follows"]
                 if f.get("post_id") == post_id and f.get("user_id") == user_id),
                None,
            )
            self._last_result = {"id": fol["id"]} if fol else None

        elif q.startswith("delete from forum_follows where id"):
            fol_id = int(params[0])
            antes = len(self.state["forum_follows"])
            self.state["forum_follows"] = [f for f in self.state["forum_follows"] if f["id"] != fol_id]
            self.rowcount = antes - len(self.state["forum_follows"])

        elif q.startswith("insert into forum_follows"):
            post_id, user_id, created_at = params
            new_id = max((f["id"] for f in self.state["forum_follows"]), default=0) + 1
            self.state["forum_follows"].append({
                "id": new_id, "post_id": post_id, "user_id": user_id, "created_at": created_at,
            })
            self._last_result = {"id": new_id}
            self.rowcount = 1

        # --- REPORTS ---
        elif q.startswith("select id, user_id, status from forum_posts where id"):
            post_id = int(params[0])
            post = next((p for p in self.state["forum_posts"] if p["id"] == post_id), None)
            self._last_result = {"id": post["id"], "user_id": post.get("user_id"), "status": post.get("status", "active")} if post else None

        elif q.startswith("select id from forum_reports where reporter_id = %s and post_id = %s"):
            reporter_id, post_id = int(params[0]), int(params[1])
            report = next(
                (r for r in self.state["forum_reports"]
                 if r.get("reporter_id") == reporter_id and r.get("post_id") == post_id
                 and r.get("status") in ("pending", "reviewed")),
                None,
            )
            self._last_result = {"id": report["id"]} if report else None

        elif q.startswith("select id, post_id, user_id, status from forum_replies where id"):
            reply_id = int(params[0])
            reply = next((r for r in self.state["forum_replies"] if r["id"] == reply_id), None)
            self._last_result = {
                "id": reply["id"], "post_id": reply.get("post_id"),
                "user_id": reply.get("user_id"), "status": reply.get("status", "active"),
            } if reply else None

        elif q.startswith("select id from forum_reports where reporter_id = %s and reply_id = %s"):
            reporter_id, reply_id = int(params[0]), int(params[1])
            report = next(
                (r for r in self.state["forum_reports"]
                 if r.get("reporter_id") == reporter_id and r.get("reply_id") == reply_id
                 and r.get("status") in ("pending", "reviewed")),
                None,
            )
            self._last_result = {"id": report["id"]} if report else None

        elif q.startswith("insert into forum_reports") and "returning id" in q:
            reporter_id, post_id, reply_id, reason, explanation, created_at = params
            new_id = max((r["id"] for r in self.state["forum_reports"]), default=0) + 1
            self.state["forum_reports"].append({
                "id": new_id, "reporter_id": reporter_id,
                "post_id": post_id, "reply_id": reply_id,
                "reason": reason, "explanation": explanation,
                "status": "pending", "admin_note": None,
                "resolved_by": None, "resolved_at": None,
                "created_at": created_at,
            })
            self._last_result = {"id": new_id}
            self.rowcount = 1

        elif q.startswith("select count(*) as total from forum_reports"):
            self._last_result = {"total": len(self.state["forum_reports"])}

        elif q.startswith("select id, status from forum_reports where id"):
            report_id = int(params[0])
            report = next((r for r in self.state["forum_reports"] if r["id"] == report_id), None)
            self._last_result = {"id": report["id"], "status": report.get("status", "pending")} if report else None

        elif q.startswith("update forum_reports set status"):
            status, admin_note, reviewed_by, reviewed_at, report_id = params
            for r in self.state["forum_reports"]:
                if r["id"] == report_id:
                    r["status"] = status
                    r["admin_note"] = admin_note
                    r["resolved_by"] = reviewed_by
                    r["resolved_at"] = reviewed_at
                    self.rowcount = 1
                    break

        # --- RATE LIMITS ---
        elif q.startswith("insert into forum_rate_limits"):
            pass

        elif q.startswith("select count(*) as cnt from forum_rate_limits"):
            self._last_result = {"cnt": 0}

        # --- AUDIT LOG ---
        elif q.startswith("insert into forum_audit_log"):
            self.state["forum_audit_log"].append(params)
            self.rowcount = 1

        elif q.startswith("select count(*) as total from forum_audit_log"):
            self._last_result = {"total": len(self.state["forum_audit_log"])}

        elif q.startswith("select fal.id, fal.admin_id, fal.action, fal.target_type, fal.target_id, fal.details, fal.created_at, u.username as admin_name from forum_audit_log fal"):
            self._last_result = []

        elif q.startswith("select fal.*, u.username as admin_username from forum_audit_log fal"):
            self._last_result = []

        # --- USER ACTIVITY ---
        elif q.startswith("select count(*) as total from forum_replies where user_id = %s and status != 'deleted'"):
            uid = int(params[0])
            self._last_result = {
                "total": len([r for r in self.state["forum_replies"]
                              if r.get("user_id") == uid and r.get("status") != "deleted"])
            }

        elif q.startswith("select count(*) as total from forum_replies fr"):
            uid = int(params[0])
            self._last_result = {
                "total": len([r for r in self.state["forum_replies"]
                              if r.get("user_id") == uid and r.get("is_accepted") and r.get("status") == "active"])
            }

        elif q.startswith("select fp.id, fp.title, fp.slug, fp.created_at, fc.name as category_name, fc.icon as category_icon from forum_posts fp"):
            uid = int(params[0])
            posts = [p for p in self.state["forum_posts"]
                     if p.get("user_id") == uid and p.get("status") != "deleted"]
            result = []
            for p in posts:
                cat = next((c for c in self.state["forum_categories"] if c["id"] == p.get("category_id")), None)
                result.append({
                    "id": p["id"], "title": p["title"], "slug": p.get("slug", ""),
                    "created_at": p["created_at"],
                    "category_name": cat["name"] if cat else None,
                    "category_icon": cat.get("icon") if cat else None,
                })
            result.sort(key=lambda p: p["created_at"], reverse=True)
            self._last_result = result[:5]

        # --- REPLIES (admin - status count adjustments) ---
        elif q.startswith("update forum_posts set reply_count = reply_count - 1 where id"):
            post_id = int(params[0])
            for p in self.state["forum_posts"]:
                if p["id"] == post_id:
                    p["reply_count"] = max(p.get("reply_count", 0) - 1, 0)
                    break

        # ── FIN FORO ────────────────────────────────────────────────────

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
            "next_featured_id": 1,
            "rayos_transactions": [],
            "qr_visits": [],
            "ai_consumption": [],
            "ai_conversations": [],
            "ai_messages": [],
            "next_conversation_id": 1,
            "next_message_id": 1,
            "featured_books": [],
            "forum_categories": [],
            "forum_posts": [],
            "forum_replies": [],
            "forum_likes": [],
            "forum_bookmarks": [],
            "forum_follows": [],
            "forum_reports": [],
            "forum_audit_log": [],
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
