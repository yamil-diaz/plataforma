"""Base de datos simulada (en memoria) para las pruebas de integración.

Replica el subconjunto de comportamiento de PostgreSQL/RealDictCursor que
usan los endpoints bajo prueba (SELECT/RETURNING/fetchone/fetchall, commit,
rollback, close). Las pruebas NO tocan ninguna base de datos real.
"""


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

        elif q.startswith("insert into reading_sessions") or q.startswith("insert into reading_progress"):
            pass

        elif q.startswith("insert into reading_daily_pages"):
            self.rowcount = 0

        elif q.startswith("update users set rayos_balance") and "returning rayos_balance" in q:
            user = self.state["users"].get(int(params[2]))
            if user:
                user["rayos_balance"] = user.get("rayos_balance", 0) + params[0]
                self._last_result = {"rayos_balance": user["rayos_balance"]}
                self.rowcount = 1

        elif q.startswith("select id from users where id") and "for update" in q:
            self._last_result = {"id": int(params[0])}

        elif q.startswith("insert into rayos_transactions"):
            self.rowcount = 1

        elif q.startswith("select interaction_type from book_interactions"):
            self._last_result = None

        else:
            raise RuntimeError(
                f"FakeCursor no implementado para la query: {query!r} con params {params!r}"
            )

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
            "log": [],
        }
        for uid, name, email, role in [
            (1, "Admin", "admin@test.com", "admin"),
            (2, "Uploader", "uploader@test.com", "user"),
            (3, "Tercero", "tercero@test.com", "user"),
        ]:
            self.state["users"][uid] = _make_user(uid, name, email, role)

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

    def cursor(self):
        return FakeCursor(self.state)

    def commit(self):
        pass

    def rollback(self):
        pass

    def close(self):
        pass